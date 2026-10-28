import os
import shutil
import sys

from lib.db.models.config import config
from lib.db.models.file import id
from lib.db.models.file_parameter import delete_parameter_files
from lib.db.queries.file import get_file_ids_with_pscid, delete_file, 

from lib.exitcode import INVALID_ARG
from lib.lorisgetopt import LorisGetOpt

def main():
    usage = (
        "\n"

        "********************************************************************\n"
        " DELETE MRI File \n"
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
            "value": None, "required": True, "expect_arg": False, "short_opt": "i", "is_path": False
        },    
        "confirm": {
            "value": None, "required": False, "expect_arg": False, "short_opt": "c", "is_path": False
        },
        "deleteondisk": {
            "value": None, "required": False, "expect_arg": False, "short_opt": "d", "is_path": False
        },
        "help": {
            "value": False, "required": False, "expect_arg": False, "short_opt": "h", "is_path": False
        },
    }

    # ---------------------------------------------------------------------------------------------
    # Get the options provided by the user
    # ---------------------------------------------------------------------------------------------
    loris_getopt_obj = LorisGetOpt(usage, options_dict, os.path.basename(__file__[:-3]))
    pscid = loris_getopt_obj.options_dict['pscid']['value']
    confirm = loris_getopt_obj.options_dict['confirm']['value']
    deleteondisk = loris_getopt_obj.options_dict['deleteondisk']['value']
    verbose = loris_getopt_obj.options_dict['verbose']['value']

    # ---------------------------------------------------------------------------------------------
    # Establish database connection
    # ---------------------------------------------------------------------------------------------
    db = Database(loris_getopt_obj.config_info.mysql, verbose)
    db.connect()

    # ---------------------------------------------------------------------------------------------
    # Load the configs
    # ---------------------------------------------------------------------------------------------
    config_db_obj = Config(db, verbose)
    data_path = config_db_obj.get_config("dataDirBasepath")

    # ---------------------------------------------------------------------------------------------
    # Load database lib objects
    # ---------------------------------------------------------------------------------------------
    
    #deprecated
    param_file_obj = ParameterFile(db, verbose)
    files_obj = Files(db, verbose)

    # ---------------------------------------------------------------------------------------------
    # Run the script
    # ---------------------------------------------------------------------------------------------
    files_obj.get_file_ids_with_pscid(db, file_id)

    for file_id in get_file_ids_with_pscid(session, pscid):
        delete_bids_file(db, file_id, confirm, deleteondisk)
        delete_pics(db,file_id)
        delete_file_in_db(db, file_id)

    db.disconnect()

def get_file_ids(db, pscid):

    file_ids = files_obj.get_file_by_pscid()

    if (count(file_ids) == 0):
        print(f"\nPSCID : {pscid} does not have entries in the files table.\n")
        #exit code

    else:
        return file_ids

def delete_file_in_db(db, file_id):

    parameter_files = param_file_obj.get_parameter_files(file_id)

    if count(parameter_files) == 0:
        print(f'\nparameters for file_id {file_id} not found. Skipping')
            continue

    if confirm:
        print(f"\nDropping all DB entries for MRI file: {file_id}\n")
        print("----------------------------\n")

    delete_param = param_file_obj.delete_parameter_files(file_id)
    #some kind of exit code if a problem

    delete_file_id = files_obj.delete_file(db, file_id):
    #some kind of exit code if a problem

    else:
        for pf in parameter_files:
            print(f'\nWould delete ParameterFileID {pf}')
            
    Return None

#use ORM
def delete_bids_file(db, file_id)
    
    file_path = db.pselect(
        """
        SELECT File FROM files WHERE FileID = '%s'
        """,
        (file_id,)
    )

    if file_path == None or '':
        print(f'\ndatabase entry for {file_path} not in db')

    if deleteondisk:
        print(f"\nDeleting {file_path}\n")
        print("----------------------------\n")

        os.remove(os.path.join(data_path, file_path))
            except Exception as e:
                print(f"Caught exception: {e} \n")

    else:
        print(f'\nWould have deleted {file_path} from disk')
        print("\nRun with --deleteondisk to delete.\n")

def delete_pic(db_file_id)

    file_paths = db.select(
        """
        SELECT Value FROM parameter_file WHERE ParameterTypeID = 
        (SELECT ID FROM parameter_type WHERE Name = 'check_pic_filename') AND 
        FileID = %s
        """,
        (file_id,)
    )

    for file_path in file_paths:
        
        if deleteondisk:
        os.remove(os.path.join(data_path, file_path))
            except Exception as e:
                print(f"Caught exception: {e} \n")

        else:
            print(f'\nWould delete {file_path}')

if __name__ == "__main__":
    main()


duplicates = [
    Q1K0000017,Q1K0000110,Q1K0000114,Q1K0000115,Q1K0000116,Q1K0000117,Q1K0000118,
    Q1K0000119,Q1K0000120,Q1K0000121,Q1K0000122,Q1K0000123,Q1K0000126,Q1K0000127,
    Q1K0000128,Q1K0000129,Q1K0000130,Q1K0000136,Q1K0000144,Q1K0000146,Q1K0000147,
    Q1K0000201,Q1K0000202,Q1K0000203,Q1K0000204,Q1K0000207,Q1K0000208,Q1K0000215,
    Q1K0000276,Q1K0000277,Q1K0000285,Q1K0000287,Q1K0000341
    ]

    use session.commit()