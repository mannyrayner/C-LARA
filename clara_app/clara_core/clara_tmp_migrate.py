
from .clara_audio_repository import AudioRepository
from .clara_database_adapter import connect, localise_sql_query

import os

##def migrate_audio_metadata_table():
##    
##    sql_command = "ALTER TABLE metadata ADD COLUMN context TEXT;"
##
##    repository = AudioRepository()
##    db_connection = connect(repository.db_file)
##    cursor = db_connection.cursor()
##    
##    # Execute the SQL command to add the 'context' column
##    try:
##        cursor.execute(sql_command)
##        db_connection.commit()
##        print("Migration completed successfully.")
##    except Exception as e:
##        db_connection.rollback()
##        print(f"Migration failed: {e}")
##    finally:
##        cursor.close()


def migrate_audio_metadata_table():
    # SQL command to add the 'context' column if it doesn't exist
    add_column_command = "ALTER TABLE metadata ADD COLUMN context TEXT DEFAULT '';"

    # SQL command to update rows where 'context' is null to empty string
    update_rows_command = "UPDATE metadata SET context = '' WHERE context IS NULL;"

    repository = AudioRepository()
    db_connection = connect(repository.db_file)
    cursor = db_connection.cursor()
    
    try:
        # Execute the SQL command to add the 'context' column
        cursor.execute(add_column_command)
        db_connection.commit()
        print("Column 'context' added successfully.")

        # Execute the SQL command to update rows
        cursor.execute(update_rows_command)
        db_connection.commit()
        print("Rows with null 'context' updated to empty string successfully.")
    except Exception as e:
        db_connection.rollback()
        print(f"Migration failed: {e}")
    finally:
        cursor.close()
        db_connection.close()



