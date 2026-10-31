import os
import shutil
import sys
import glob
from sqlalchemy.orm import Session as Database

from lib.config import get_data_dir_path_config

from lib.db.models import config
from lib.db.models import file
from lib.db.models import file_parameter

from lib.db.queries.config import try_get_config_with_setting_name
from lib.db.queries.file import get_file_ids_with_pscid, delete_file_id, try_get_path_with_file_id
from lib.db.queries.file_parameter import delete_file_parameters, try_get_pic_paths_with_file_id

from lib.exitcode import INVALID_ARG
from lib.lorisgetopt import LorisGetOpt

def main():
    usage = (
        "\n"

        "********************************************************************\n"
        " DELETE MRI BIDS \n"
        "********************************************************************\n"
        "This script deletes all the MRI bids data associated with an PSCID"

        "usage  : delete_mri_bids.py --pscid <pscid> --deleteondisk --confirm\n\n"

        "options: \n"
        "\t-p, --profile      : Name of the python database config file in config\n"
        "\t-i  --pscid,       : pscid of candidate to delete mri bids\n"
        "\t-c, --confirm      : After a trial run, perform the deletion\n"
        "\t-d, --deleteondisk : Delete files on disk\n"

        "required options are: \n"
        "\t--fileid\n"
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
            "value": None, "required": False, "expect_arg": False, "short_opt": "f", "is_path": True
        },
        #cbigr override close
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

    # ---------------------------------------------------------------------------------------------
    # Get the database
    #----------------------------------------------------------------------------------------------
    
    db = loris_getopt_obj.env.db
    
    #----------------------------------------------------------------------------------------------
    # Get paths
    #----------------------------------------------------------------------------------------------

    data_path = try_get_config_with_setting_name(db, 'dataDirBasepath').value
    #print(f' DATA DIR BASE PATH ISSSSSSSSSSSSSSSSSSSSSSSSS {data_path}')
    # bids_path = data_path + 'bids_imports/' + project_folder
    # print(f' BIDS PATH ISSSSSSSSSSSSSSSSSSSSSSSSSSSSSS {bids_path}')
    pics_path = data_path + 'pic'
    #print(f' PIC PATH ISSSSSSS {pics_path}')

    # ---------------------------------------------------------------------------------------------
    # Run the script
    # ---------------------------------------------------------------------------------------------

    deleted = 0
    try:
        for file_id in get_file_ids_with_pscid(db, pscid):
            
            #delete_pics(db,file_id, pics_path, deleteondisk)
#==================================================================
            result = delete_file_parameters(db, file_id)
            if result:
                print(f"File {file_id}: {result.rowcount} parameter row(s) deleted") 
            else:
                print(f'no file parameters found for file id : {file_id}')

        if confirm:
            db.commit()
            print("Deletion committed.")

        else:
            db.rollback()
            print("trial run:. Use --confirm to delete")
#==================================================================
        #     result = delete_file(db, file_id)  

        #     if result is not None and result.rowcount > 0:
        #         print(f"File {file_id}: {result.rowcount} deleted")
        #         deleted += result.rowcount
        #     else:
        #         print(f"No entry deleted from file table for file id {file_id}")

        # if deleted == 0:
        #     db.rollback()
        #     print("Nothing to delete.")
        # elif confirm:
        #     db.commit()
        #     print(f"{deleted} row(s) deleted and committed.")
        # else:
        #     db.rollback()
        #     print(f"Trial run: {deleted} row(s) would be deleted. Use --confirm to delete.")
                    
            delete_bids_file(db, file_id, data_path, deleteondisk)
        # delete_dirs(bids_path, pscid, deleteondisk)
        # delete_participant_tsv_line(bids_path, pscid, deleteondisk)
    except Exception:
        db.rollback()
        raise
#-------------------------------------------------------------------------------------------------
# Helpers
#-------------------------------------------------------------------------------------------------

def delete_pics(db, file_id, pics_path, deleteondisk):
    """Delete the pics associated to the file_id queried in parameter_file table"""

    pic_paths = try_get_pic_paths_with_file_id(db, file_id)
    pic_dirs = set()

    for path in pic_paths:
        full_path = os.path.join(pics_path, path)
        pic_dirs.add(os.path.dirname(full_path))
        
        if deleteondisk:
            try:
                os.remove(os.path.join(pics_path, path))
                print(f'\nDeleted {path}')
            except OSError as e:
                print(f"Couldn't delete {path}: {e}")

        else:
            print(f'\nWould delete {path}')

    for pic_dir in pic_dirs:
        delete_dir_if_empty(pic_dir, deleteondisk)

def delete_bids_file(db, file_id, data_path, deleteondisk):
    """Delete the file that was queried by file id on disk"""

    file_path = try_get_path_with_file_id(db, file_id)
    full_path = os.path.join(data_path, file_path)
    print(f'FULL PATH IS {full_path}')    

    if deleteondisk:
        try: 
            os.remove(os.path.join(data_path, file_path))
        except OSError as e:
            print(f"Couldn't delete {file_path}: {e}")
        
        delete_sidecars(full_path, deleteondisk)

    else:
        print(f'\nWould have deleted {file_path} from disk')


def delete_sidecars(image_path, deleteondisk):
    """Delete the sidecar files (json, bval, bvec) next to a NIfTI image"""

    sidecar_extensions = ['.json', '.bval', '.bvec']

    if image_path.endswith('.nii.gz'):
        base = image_path[:-len('.nii.gz')]
    elif image_path.endswith('.nii'):
        base = image_path[:-len('.nii')]
    else:
        return

    for ext in sidecar_extensions:
        sidecar = base + ext
        if not os.path.isfile(sidecar):
            continue

        if deleteondisk:
            try:
                os.remove(sidecar)
                print(f'\nDeleted {sidecar}')
            except OSError as e:
                print(f"Couldn't delete {sidecar}: {e}")
        else:
            print(f'\nWould delete {sidecar}')

def delete_dirs(bids_path, pscid, deleteondisk):
    """Delete MRI modality dirs for a participant if they are empty"""
    
    subject_dir = os.path.join(bids_path, 'sub-' + pscid)
    
    if not os.path.isdir(subject_dir):
        print(f'{subject_dir} does not exist. Skipping')
        return
    
    modalities = ['anat', 'dwi', 'fmap', 'func']

    for session_dir in glob.glob(os.path.join(subject_dir, 'ses-*')):
        for modality in modalities:
            modality_dir = os.path.join(session_dir, modality)
            if os.path.isdir(modality_dir):
                delete_folder_if_empty(modality_dir, deleteondisk)
        
        delete_dir_if_empty(session_dir, deleteondisk)
    
    delete_dir_if_empty(subject_dir, deleteondisk)

    return None

def delete_dir_if_empty(folder_path, deleteondisk):
    """Delete the folder if it exists and is empty"""

    if not os.path.isdir(folder_path):
        return

    if os.listdir(folder_path):
        print(f'\nNot deleting {folder_path}, folder is not empty')
        return

    if deleteondisk:
        try:
            os.rmdir(folder_path)
            print(f'\nDeleted empty folder {folder_path}')

        except OSError as e:
            print(f'Caught exception: {e}\n')
    else:
        print(f'\nWould delete empty folder {folder_path}')

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
        print(f'{participant_id} not found in {tsv_path}')
        return

    if deleteondisk:
        tmp_path = tsv_path + '.tmp'
        with open(tmp_path, 'w', newline='') as f:
            f.writelines(kept)
        os.replace(tmp_path, tsv_path)
        print(f'Removed {participant_id} from {tsv_path}')
    else:
        print(f'Would remove {participant_id} from {tsv_path}')

if __name__ == "__main__":
    main()
