import os
import shutil
import sys

from lib.database import Database
from lib.database_lib.config import Config
from lib.exitcode import INVALID_ARG
from lib.lorisgetopt import LorisGetOpt

def main():
    usage = (
        "\n"

        "********************************************************************\n"
        " DELETE MRI File \n"
        "********************************************************************\n"
        "This script deletes all the MRI bids data associated with an PSCID"

        "usage  : delete_mri_bids.py -f file_id -p <profile> ...\n\n"

        "options: \n"
        "\t-p, --profile      : Name of the python database config file in config\n"
        "\t-i  --pscid        : pscid of candidate to delete mri bids
        "\t-c, --confirm      : After a trial run, perform the deletion\n"
        "\t-d, --deleteondisk : Delete files on disk\n"
        "\t-v, --verbose      : If set, be verbose\n\n"

        "required options are: \n"
        "\t--fileid\n"
    )

    options_dict = {
        "profile": {
            "value": None, "required": False, "expect_arg": True, "short_opt": "p", "is_path": False
        }, 
        "pscid": { 
            "value": None, "required": False, "expect_arg": False, "short_opt": "i", "is_path": False
        },    
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
    # Run the script
    # ---------------------------------------------------------------------------------------------
    get_file_ids(db, file_id)

    for file_id in file_ids:
        delete_bids_file(db, file_id, confirm, deleteondisk)
        delete_pics(db,file_id)
        delete_file_in_db(db, file_id)

    db.disconnect()

def get_file_ids(db, pscid):
    """
    Check that this candidate has mri bids in the database

    :param db: database object from the database.py class
     :type db: Database
    :param pscid
     :type pscid: str
    :return array
    """

    file_ids = db.pselect(
        """
        SELECT 
        FileID, File FROM files f
        JOIN session s ON f.SessionID = s.ID
        JOIN Project p ON s.ProjectID = project_id
        JOIN candidate c ON c.CandID = s.CandID
        WHERE c.PSCID = '%s';
        """
    )

    if (count(file_ids) == 0):
        print(f"\nPSCID : {pscid} does not have entries in the files table.\n")
        sys.exit(INVALID_ARG)

    else:
        return file_ids

def delete_file_in_db(db, file_id):

    parameter_file_ids = db.pselect(
        """
        SELECT ParameterFileID FROM parameter_file pf WHERE pf.FileID = %s;
        """,
        (file_id,)
    )

    if count(parameter_file_ids) == 0:
        print(f'\nparameters for file_id {file_id} not found. Skipping')
            continue

    if confirm:
        print(f"\nDropping all DB entries for MRI file: {file_id}\n")
        print("----------------------------\n")

        db.update(
            """
            DELETE FROM parameter_files WHERE FileID = %s
            """,
            (file_id,) 
        )

        #delete the entry from files table
        db.update(
            """
            "DELETE FROM files WHERE file_id = %s"
            """,
            (file_id,)
        )
        print(f'\ndeleted file_id {file_id}')

    else:
        param_id_value = {}
        param_id_value = db.pselect(
            """
            SELECT ParameterFileID, Value FROM parameter_file WHERE File ID = %s
            """,
            (file_id,)
        )
        for k,v in param_id_value.items:
            print(f'\nWould delete ParameterFileID {k} and Value {v}')
            

    Return None


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