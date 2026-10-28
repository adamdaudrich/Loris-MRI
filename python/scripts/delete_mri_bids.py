import os
import shutil
import sys

# use sqlalchemy.orm.Session to communicate with the database
# Usually, database session variables are named db and the 
# SQLAlchemy Session is renamed to Database to not conflict with the LORIS concept of a session 2.
from sqlalchemy.orm import Session as Database

#The SQLAlchemy models are defined in the lib.db.models module. 
#Each file contains a single SQLAlchemy model that is linked to 
#a given LORIS SQL table. A model file should be named model_name.py 
#and a model class should be named DbModelName. 
#A model describes the structure of its table and its relations 
#with other models. Do not import model classes directly in other 
#models as this can create cyclic dependencies that Python 
#cannot handle.

#An SQLAlchemy model and its attributes can be renamed compared 
#to the LORIS SQL schema to adhere to the Python naming conventions,
# avoid repetitions, and provide a more consistent database abstraction.

#There is an integration test to ensure the SQLAlchemy models 
#remain synchronized with the LORIS SQL schema.

from lib.db.models import config
from lib.db.models import file
from lib.db.models import file_parameter


# The SQLAlchemy queries are defined in the lib.db.queries module. 
#This module is divided in submodules that group queries by theme 
#(for instance lib.db.queries.candidate for candidate-related queries).

# All the LORIS-MRI SQLAlchemy queries should go in lib.db.queries, doing so
# allows to make queries more discoverable, reusable, and to isolate them 
# from the rest of the code logic.

# Each query should be encapsulated in a function that takes the 
#database session and the query parameters as arguments, and 
#returns the query results, None, or pass through the SQLAlchemy 
#exception in case of error. The query functions should not contain 
#any error handling, logging, transaction management, or complex logic. 
# This work should be delegated to the caller.

# When possible, queries should also be written in a generalized 
#way that make them easily reusable by other parts of the code. 
#For instance, it is often preferable for a query to return a whole model object instead of only some of its fields as different callers might be interested in different fields. Micro-optimization should be avoided unless a query is called in a particularly performance-sensitive section of the code.
# Finally, model relations should be preferred to queries where 
#they do not blow up the complexity of the code (such as in a 
#nested loop).

from lib.db.queries.file import get_file_ids_with_pscid, delete_file, try_get_path_with_file_id
from lib.db.queries.file_parameter import delete_file_parameters

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
            "value": None, "required": True, "expect_arg": True, "short_opt": "i", "is_path": False
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
    #loris_getopt_obj = LorisGetOpt(usage, options_dict, os.path.basename(__file__[:-3]))  
    loris_getopt_obj = LorisGetOpt(usage, options_dict, 'delete_mri_bids')
    pscid = loris_getopt_obj.options_dict['pscid']['value']
    confirm = loris_getopt_obj.options_dict['confirm']['value']
    deleteondisk = loris_getopt_obj.options_dict['deleteondisk']['value']

    db = loris_getopt_obj.env.db
    # ---------------------------------------------------------------------------------------------
    # Run the script
    # ---------------------------------------------------------------------------------------------

    for file_id in get_file_ids_with_pscid(db, pscid):
#        delete_pics(db,file_id)
        # result = delete_file_parameters(db, file_id)
        # print(f"File {file_id}: {result.rowcount} parameter row(s) deleted") 
#        delete_bids_file(db, file_id)
        # resultt = delete_file(db, file_id)
        # print(f"File {file_id}: {resultt.rowcount} deleted")
        #delete the empty mri modality directory


def delete_bids_file(db, file_id):

    file_paths = try_get_path_with_file_id(db, file_id)    
    # for file in file_paths:
    #     print(f"{i}")

    if deleteondisk:
        print(f"\nDeleting {file}\n")
        print("----------------------------\n")

         os.remove(os.path.join(data_path, file))
             except Exception as e:
                print(f"Caught exception: {e} \n")

    else:
        print(f'\nWould have deleted {file_path} from disk')
        print("\nRun with --deleteondisk to delete.\n")

def delete_pic(db, file_id)

    pic_paths = try_get_pic_paths_with_file_id(db, file_id):

    for path in pic_paths:
        
        if deleteondisk:
        os.remove(os.path.join(data_path, path))
            except Exception as e:
                print(f"Caught exception: {e} \n")

        else:
            print(f'\nWould delete {path}')

if __name__ == "__main__":
    main()


# duplicates = [
#     Q1K0000017,Q1K0000110,Q1K0000114,Q1K0000115,Q1K0000116,Q1K0000117,Q1K0000118,
#     Q1K0000119,Q1K0000120,Q1K0000121,Q1K0000122,Q1K0000123,Q1K0000126,Q1K0000127,
#     Q1K0000128,Q1K0000129,Q1K0000130,Q1K0000136,Q1K0000144,Q1K0000146,Q1K0000147,
#     Q1K0000201,Q1K0000202,Q1K0000203,Q1K0000204,Q1K0000207,Q1K0000208,Q1K0000215,
#     Q1K0000276,Q1K0000277,Q1K0000285,Q1K0000287,Q1K0000341
#     ]

#     use session.commit()