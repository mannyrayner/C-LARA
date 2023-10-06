class ImageRepository:
    def __init__(self, callback=None):   
        self.db_file = absolute_local_file_name(config.get('image_repository', ('db_file' if _s3_storage else 'db_file_local')))
        self.base_dir = absolute_file_name(config.get('image_repository', 'base_dir'))
        self._initialize_repository(callback=callback)

    def _initialize_repository(self, callback=None):
        # Similar initialization logic as AudioRepository
        # ...

    def delete_entries_for_project(self, project_id, callback=None):
        # Logic to delete all images associated with a specific project
        # ...

    def add_entry(self, project_id, image_name, file_path, associated_text=None, associated_areas=None, callback=None):
        # Logic to add an image entry to the repository
        # ...

    def get_entry(self, project_id, image_name, callback=None):
        # Logic to retrieve an image entry from the repository
        # ...

    def get_project_directory(self, project_id):
        # Returns the directory path where images for a specific project are stored
        return absolute_file_name(Path(self.base_dir) / project_id)

    def store_image(self, project_id, source_file, keep_file_name=True):
        # Logic to store an image file in the repository
        # ...
