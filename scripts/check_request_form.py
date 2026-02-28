import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','npdc_site.settings')
django.setup()

from data_submission.forms import DatasetRequestForm
from django.contrib.auth.models import User
from data_submission.models import DatasetSubmission

def run():
    u = User.objects.create_user('tester','tester@example.com','pwd')
    sub = DatasetSubmission.objects.create(
        title='foo',submitter=u,temporal_start_date='2000-01-01',temporal_end_date='2000-01-02',
        west_longitude=0,east_longitude=1,south_latitude=0,north_latitude=1,contact_email='a@b.com'
    )
    sub.data_file.save('x.pdf', __import__('django').core.files.base.ContentFile(b'pdf'))
    post_data={
        'first_name':'Rahul','last_name':'Das','email':'rahul@example.com','institute':'NPDC','country':'India','research_area':'Polar','purpose':'Test','agree_cite':True,'agree_share':False,'captcha_0':'dummy','captcha_1':'PASSED'
    }
    form=DatasetRequestForm(post_data)
    print('form valid?', form.is_valid())
    print('errors', form.errors)

if __name__ == '__main__':
    run()
