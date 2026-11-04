import argparse
import sys

from collections import Counter
from pathlib import Path

from lib.config import get_data_dir_path_config
from lib.env import Env
from lib.make_env import make_env
from lib.exitcode import INVALID_ARG

from lib.db.queries.config import try_get_config_with_setting_name
from lib.d
from lib.db.queries.file import try_get_file_with_id, get_files_with_candidate_id, delete_file_entry
from lib.db.queries.file_parameter import delete_file_parameters, try_get_pic_paths_with_file_id

from loris_bids_utils.files.participants import BidsParticipantsTsvFile

# from lib.lorisgetopt import LorisGetOpt

# Set from --verbose in main(). When False, only summaries and errors are printed.
VERBOSE = False

# Counts of disk actions, reported in the summary at the end of the run
disk_counts = Counter()


def vprint(*args, **kwargs):
    """Print only when --verbose is set"""
    if VERBOSE:
        print(*args, **kwargs)


def main():
    global VERBOSE

    parser = argparse.ArgumentParser(
        description="Delete database entries, niftis, sidecars, and pics for a given candidate"
    )

    parser.add_argument(
        '-p', '--profile',
        help="Name of the python database config file in the config directory."
    )
    
    parser.add_argument(
        '-i', '--pscid',
        type=str,
        required=True,
        help="The PSCID associated with the candidate's data you wish to delete"
    )

    parser.add_argument(
        '-f', '--project_bids_dir',
        type=str,
        required=True,
        help="Name of the directory containing the CBIGR project's bids"
    )

    parser.add_argument(
        '-c', '--confirm',
        action='store_true'
        help="Commits database entry deletion"
    )

    parser.add_argument(
        '-d', '--deleteondisk',
        action='store_true',
        help="Deletes targeted file(s) on disk"
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Provide verbose output'
    )

    args = parser.parse_args()

    #set args
    config_file = load_config(args.profile)
    pscid = args.pscid
    project_folder = args.project_bids_dir
    confirm = args.confirm
    deleteondisk = args.deletondisk
    VERBOSE = args.verbose
    
    #set environment
    env = make_env('delete_mri_bids', {}, config_file, args.verbose)
    
    #set data dir base path
    data_path = get_data_dir_path_config(env)

    #data_path = try_get_config_with_setting_name(env.db, 'dataDirBasepath').value
    pics_path = data_path /'pic'
    bids_path = data_path / 'bids_imports' / project_folder

    if not bids_path.is_dir():
        print(f'{bids_path} does not exist. Check --project_bids_dir')
        sys.exit(INVALID_ARG)

    # ---------------------------------------------------------------------------------------------
    # Run the script
    # ---------------------------------------------------------------------------------------------

    deleted_files = 0
    deleted_params = 0
    try:
        #provide error message here if None is returned
        candidate_id = try_get_candidate_with_pscid(env.db, pscid)

        file_ids = get_files_with_candidate_id(env.db, candidate_id)
        print(f'Found {len(file_ids)} file(s) in the database for PSCID {pscid}')

        # Per-file cleanup: disk first (needs the DB rows to look up paths), then DB rows
        for file_id in file_ids:
            vprint(f'\n--- File ID {file_id} ---')

            try:
                delete_pics(db, file_id, pics_path, deleteondisk)
                delete_bids_file(env.db, file_id, data_path, deleteondisk)
            except Exception as e:
                print(f'Disk cleanup failed for file {file_id}: {e}. Continuing.')

            result = delete_file_parameters(env.db, file_id)
            n = result.rowcount if result is not None else 0
            vprint(f'{n} parameter row(s) for file {file_id}')
            deleted_params += n

            result = delete_file_entry(env.db, file_id)
            n = result.rowcount if result is not None else 0
            vprint(f'{n} file row(s) for file {file_id}')
            deleted_files += n

        # Participant-level BIDS cleanup, runs even if no files were found in the database
        vprint(f'\n--- BIDS folders for sub-{pscid} in {bids_path} ---')
        try:
            delete_dirs(bids_path, pscid, deleteondisk)
            delete_participant_tsv_line(bids_path, pscid, deleteondisk)
        except Exception as e:
            print(f'BIDS folder cleanup failed: {e}. Continuing.')

        # Disk summary
        verb = 'deleted' if deleteondisk else 'would be deleted'
        print(f'\nDisk: {disk_counts["images"]} image(s), {disk_counts["sidecars"]} sidecar(s), '
              f'{disk_counts["pics"]} pic(s), {disk_counts["folders"]} empty folder(s) {verb}')
        if disk_counts['missing']:
            print(f'{disk_counts["missing"]} image(s) recorded in the database were already missing on disk')

        # Database summary
        if deleted_files == 0 and deleted_params == 0:
            db.rollback()
            print('Database: nothing to delete.')
        elif confirm:
            db.commit()
            print(f'Database: committed, {deleted_files} file row(s) and '
                  f'{deleted_params} parameter row(s) deleted.')
        else:
            db.rollback()
            print(f'Database (trial run): {deleted_files} file row(s) and {deleted_params} '
                  f'parameter row(s) would be deleted. Use --confirm to delete.')
    except Exception:
        db.rollback()
        raise

# -------------------------------------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------------------------------------

def delete_pics(db, file_id, pics_path, deleteondisk):
    """Delete the pics associated to the file_id queried in parameter_file table"""

    pic_dirs = set()

    for path in try_get_parameter_value_with_file_id_parameter_name(
        db, file_id, 'check_pic_filename'):
        if not path:
            continue

        full_path = pics_path / path
        pic_dirs.add(os.path.dirname(full_path))

        if not full_path.is_file:
            vprint(f'{full_path} not found on disk, continuing')
            continue

        if deleteondisk:
            try:
                os.remove(full_path)
                vprint(f'Deleted {full_path}')
            except OSError as e:
                print(f"Couldn't delete {full_path}: {e}")
                continue
        else:
            vprint(f'Would delete {full_path}')
        disk_counts['pics'] += 1

    for pic_dir in pic_dirs:
        delete_dir_if_empty(pic_dir, deleteondisk)


def delete_bids_file(db, file_id, data_path: Path, deleteondisk):
    """Delete the image for file_id on disk, plus its sidecars. Never raises."""

    file = try_get_file_with_id(db, file_id)

    if file is not None:
        file_path = file.path

    else:
        return

    print(f'FILE PATH isSSSSSSSSS {file_path}')

    if not file_path:
        print(f'No path recorded for file id {file_id}, skipping disk deletion')
        return

    full_path = data_path / file_path

    if not full_path.is_file():
        vprint(f'{full_path} not found on disk, continuing')
        disk_counts['missing'] += 1
    elif deleteondisk:
        try:
            os.remove(full_path)
            vprint(f'Deleted {full_path}')
            disk_counts['images'] += 1
        except OSError as e:
            print(f"Couldn't delete {full_path}: {e}")
    else:
        vprint(f'Would delete {full_path}')
        disk_counts['images'] += 1

    # Sidecars may still exist even when the image itself is gone
    delete_sidecars(full_path, deleteondisk)


def delete_sidecars(image_path: Path, deleteondisk):
    """Delete the sidecar files (json, bval, bvec) next to a NIfTI image"""

    name = image_path.name
    if name.endswith('.nii.gz'):
        stem = name[:-len('.nii.gz')]
    elif name.endswith('.nii'):
        stem = name[:-len('.nii')]
    else:
        return

    for ext in ['.json', '.bval', '.bvec']:
        sidecar = image_path.with_name(stem + ext)
        if not sidecar.is_file():
            continue

        if deleteondisk:
            try:
                sidecar.unlink()
                vprint(f'Deleted {sidecar}')
            except OSError as e:
                print(f"Couldn't delete {sidecar}: {e}")
                continue
        else:
            vprint(f'Would delete {sidecar}')
        disk_counts['sidecars'] += 1


def delete_dirs(bids_path: Path, pscid, deleteondisk):
    """Delete MRI modality, session and subject dirs for a participant if they are empty"""

    subject_dir = bids_path / f'sub-{pscid}'

    if not subject_dir.is_dir():
        print(f'{subject_dir} does not exist. Skipping folder cleanup')
        return

    modalities = ['anat', 'dwi', 'fmap', 'func']

    for session_dir in subject_dir.glob('ses-*'):
        for modality in modalities:
            modality_dir = session_dir / modality
            if modality_dir.is_dir():
                delete_dir_if_empty(modality_dir, deleteondisk)

        delete_dir_if_empty(session_dir, deleteondisk)

    delete_dir_if_empty(subject_dir, deleteondisk)


def delete_dir_if_empty(folder_path: Path, deleteondisk):
    """Delete the folder if it exists and is empty"""

    if not folder_path.is_dir():
        return

    if any(folder_path.iterdir()):
        vprint(f'Not deleting {folder_path}, folder is not empty')
        return

    if deleteondisk:
        try:
            folder_path.rmdir
            vprint(f'Deleted empty folder {folder_path}')
        except OSError as e:
            print(f"Couldn't delete folder {folder_path}: {e}")
            return
    else:
        vprint(f'Would delete empty folder {folder_path}')
    disk_counts['folders'] += 1


def delete_participant_tsv_line(bids_path: Path, pscid: str, deleteondisk: bool):
    """Remove a participant's row from participants.tsv"""

    tsv_path = bids_path / 'participants.tsv'
    participant_id = pscid.removeprefix('sub-')

    if not tsv_path.is_file():
        print(f'{tsv_path} does not exist. Skipping')
        return

    participants_file = BidsParticipantsTsvFile(tsv_path)

    row = participants_file.get_row(participant_id)
    if row is None:
        print(f'sub-{participant_id} not found in participants.tsv')
        return

    if not deleteondisk:
        print(f'Would remove sub-{participant_id} from participants.tsv')
        return
    
    participants_file.rows.remove(row)

    tmp_path = tsv_path.with_name(tsv_path.name + '.tmp')
    participants_file.write(tmp_path)
    tmp_path.replace(tsv_path)
    print(f'Removed sub-{participant_id} from participants.tsv')

if __name__ == "__main__":
    main()