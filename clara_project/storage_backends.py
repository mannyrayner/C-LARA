from storages.backends.s3boto3 import S3Boto3Storage
import os

class MyS3Boto3Storage(S3Boto3Storage):
    # c-lara
    bucket_name = os.environ.get('S3_BUCKET_NAME')
    # https://c-lara.s3.
    endpoint_url = f'https://{bucket_name}.s3.'
    # ap-southeast-2
    region_name = os.environ.get('AWS_REGION')

    def url(self, name):
        print(name)
        url = super().url(name)
        if url.startswith('//'):
            url = 'https:%s' % url
        # Insert the region into the url after 'https://c-lara.s3.'
        return url.replace(self.endpoint_url, self.endpoint_url + self.region_name + '.')
