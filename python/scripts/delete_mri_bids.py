import os
import sys
import glob
from collections import Counter

from lib.db.queries.config import try_get_config_with_setting_name
from lib.db.queries.file import get_file_ids_with_pscid, delete_file_id, try_get_path_with_file_id
from lib.db.queries.file_parameter import delete_file_parameters, try_get_pic_paths_with_file_id

from lib.exitcode import INVALID_ARG
from lib.lorisgetopt import LorisGetOpt

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

    usage = (
        "\n"

        "********************************************************************\n"
        " DELETE MRI BIDS \n"
        "********************************************************************\n"
        "This script deletes all the MRI BIDS data associated with a PSCID\n\n"

        "usage  : delete_mri_bids.py --pscid <pscid> --project_bids_dir <folder> --deleteondisk --confirm\n\n"

        "options: \n"
        "\t-p, --profile          : Name of the python database config file in config\n"
        "\t-i, --pscid            : PSCID of the candidate whose MRI BIDS data to delete\n"
        "\t-f, --project_bids_dir : BIDS project folder name under bids_imports/\n"
        "\t-c, --confirm          : After a trial run, commit the database deletion\n"
        "\t-d, --deleteondisk     : Delete files on disk\n"
        "\t-v, --verbose          : Print every file and folder action\n\n"

        "required options are: \n"
        "\t--pscid\n"
        "\t--project_bids_dir\n"
    )

    options_dict = {
        "profile": {
            "value": None, "required": False, "expect_arg": True, "short_opt": "p", "is_path": False
        },
        "pscid": {
            "value": None, "required": True, "expect_arg": True, "short_opt": "i", "is_path": False
        },
        # cbigr override open
        "project_bids_dir": {
            "value": None, "required": True, "expect_arg": True, "short_opt": "f", "is_path": False
        },
        # cbigr override close
        "confirm": {
            "value": None, "required": False, "expect_arg": False, "short_opt": "c", "is_path": False
        },
        "deleteondisk": {
            "value": None, "required": False, "expect_arg": False, "short_opt": "d", "is_path": False
        },
        "verbose": {
            "value": False, "required": False, "expect_arg": False, "short_opt": "v", "is_path": False
        },
        "help": {
            "value": False, "required": False, "expect_arg": False, "short_opt": "h", "is_path": False
        },
    }

    # ---------------------------------------------------------------------------------------------
    # Get the options provided by the user
    # ---------------------------------------------------------------------------------------------

    loris_getopt_obj = LorisGetOpt(usage, options_dict, 'delete_mri_bids')
    pscid = loris_getopt_obj.options_dict['pscid']['value']
    project_folder = loris_getopt_obj.options_dict['project_bids_dir']['value']
    confirm = loris_getopt_obj.options_dict['confirm']['value']
    deleteondisk = loris_getopt_obj.options_dict['deleteondisk']['value']
    VERBOSE = bool(loris_getopt_obj.options_dict['verbose']['value'])

    # ---------------------------------------------------------------------------------------------
    # Get the database
    # ---------------------------------------------------------------------------------------------

    db = loris_getopt_obj.env.db

    # ---------------------------------------------------------------------------------------------
    # Get paths
    # ---------------------------------------------------------------------------------------------

    data_path = try_get_config_with_setting_name(db, 'dataDirBasepath').value
    pics_path = os.path.join(data_path, 'pic')
    bids_path = os.path.join(data_path, 'bids_imports', project_folder)

    if not os.path.isdir(bids_path):
        print(f'{bids_path} does not exist. Check --project_bids_dir')
        sys.exit(INVALID_ARG)

    # ---------------------------------------------------------------------------------------------
    # Run the script
    # ---------------------------------------------------------------------------------------------

    deleted_files = 0
    deleted_params = 0
    try:
        file_ids = list(get_file_ids_with_pscid(db, pscid))
        print(f'Found {len(file_ids)} file(s) in the database for PSCID {pscid}')

        # Per-file cleanup: disk first (needs the DB rows to look up paths), then DB rows
        for file_id in file_ids:
            vprint(f'\n--- File ID {file_id} ---')

            try:
                delete_pics(db, file_id, pics_path, deleteondisk)
                delete_bids_file(db, file_id, data_path, deleteondisk)
            except Exception as e:
                print(f'Disk cleanup failed for file {file_id}: {e}. Continuing.')

            result = delete_file_parameters(db, file_id)
            n = result.rowcount if result is not None else 0
            vprint(f'{n} parameter row(s) for file {file_id}')
            deleted_params += n

            result = delete_file_id(db, file_id)
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

    for path in try_get_pic_paths_with_file_id(db, file_id):
        if not path:
            continue

        full_path = os.path.join(pics_path, path)
        pic_dirs.add(os.path.dirname(full_path))

        if not os.path.isfile(full_path):
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


def delete_bids_file(db, file_id, data_path, deleteondisk):
    """Delete the image for file_id on disk, plus its sidecars. Never raises."""

    file_path = try_get_path_with_file_id(db, file_id)
    if not file_path:
        print(f'No path recorded for file id {file_id}, skipping disk deletion')
        return

    full_path = os.path.join(data_path, file_path)

    if not os.path.isfile(full_path):
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


def delete_sidecars(image_path, deleteondisk):
    """Delete the sidecar files (json, bval, bvec) next to a NIfTI image"""

    if image_path.endswith('.nii.gz'):
        base = image_path[:-len('.nii.gz')]
    elif image_path.endswith('.nii'):
        base = image_path[:-len('.nii')]
    else:
        return

    for ext in ['.json', '.bval', '.bvec']:
        sidecar = base + ext
        if not os.path.isfile(sidecar):
            continue

        if deleteondisk:
            try:
                os.remove(sidecar)
                vprint(f'Deleted {sidecar}')
            except OSError as e:
                print(f"Couldn't delete {sidecar}: {e}")
                continue
        else:
            vprint(f'Would delete {sidecar}')
        disk_counts['sidecars'] += 1


def delete_dirs(bids_path, pscid, deleteondisk):
    """Delete MRI modality, session and subject dirs for a participant if they are empty"""

    subject_dir = os.path.join(bids_path, 'sub-' + pscid)

    if not os.path.isdir(subject_dir):
        print(f'{subject_dir} does not exist. Skipping folder cleanup')
        return

    modalities = ['anat', 'dwi', 'fmap', 'func']

    for session_dir in glob.glob(os.path.join(subject_dir, 'ses-*')):
        for modality in modalities:
            modality_dir = os.path.join(session_dir, modality)
            if os.path.isdir(modality_dir):
                delete_dir_if_empty(modality_dir, deleteondisk)

        delete_dir_if_empty(session_dir, deleteondisk)

    delete_dir_if_empty(subject_dir, deleteondisk)


def delete_dir_if_empty(folder_path, deleteondisk):
    """Delete the folder if it exists and is empty"""

    if not os.path.isdir(folder_path):
        return

    if os.listdir(folder_path):
        vprint(f'Not deleting {folder_path}, folder is not empty')
        return

    if deleteondisk:
        try:
            os.rmdir(folder_path)
            vprint(f'Deleted empty folder {folder_path}')
        except OSError as e:
            print(f"Couldn't delete folder {folder_path}: {e}")
            return
    else:
        vprint(f'Would delete empty folder {folder_path}')
    disk_counts['folders'] += 1


def delete_participant_tsv_line(bids_path, pscid, deleteondisk):
    """Remove a participant's row from participants.tsv"""

    tsv_path = os.path.join(bids_path, 'participants.tsv')
    participant_id = f'sub-{pscid}'

    if not os.path.isfile(tsv_path):
        print(f'{tsv_path} does not exist. Skipping')
        return

    with open(tsv_path, 'r', newline='') as f:
        lines = f.readlines()

    # Keep the header and every row whose first column isn't this participant
    kept = [line for line in lines if line.split('\t')[0].strip() != participant_id]

    if len(kept) == len(lines):
        print(f'{participant_id} not found in participants.tsv')
        return

    if deleteondisk:
        tmp_path = tsv_path + '.tmp'
        with open(tmp_path, 'w', newline='') as f:
            f.writelines(kept)
        os.replace(tmp_path, tsv_path)
        print(f'Removed {participant_id} from participants.tsv')
    else:
        print(f'Would remove {participant_id} from participants.tsv')


if __name__ == "__main__":
    main()