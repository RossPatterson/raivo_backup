import click
import contextlib
#import logging
import os
from pyicloud import PyiCloudService
import pyzipper
from shutil import copyfileobj
import typing

COOKIE_FILE = r'C:\Users\Ross\AppData\Local\Temp\pyicloud\Ross\rap666icloudcom'
#LOGGER = logging.getLogger(__name__)
#LOGFILE = 'raivo_backup.log'
SESSION_FILE = r'C:\Users\Ross\AppData\Local\Temp\pyicloud\Ross\rap666icloudcom.session'

def connect_to_icloud(userid: string, password: string) -> PyiCloudService:
	"""
	Connect to the iCloud services.  Returns an API object.
	The logic for 2-step and 2-factor authentication is based on the
	sample at https://github.com/picklepete/pyicloud/blob/master/README.rst#two-step-and-two-factor-authentication-2sa2fa.
	"""
	#api = RAP_PyiCloudService(userid, password)
	#while not api.verified:
	#	if api.requires_2sa:
	#		print('Two-step authentication required.')
	#		if click.confirm('Have you received authentication request on any of your devices?'):
	#			verification_code = click.prompt('Please enter validation code from your device')
	#			api.verify_2xa('2fa', verification_code)
	#		else:
	#			print('Fallback to SMS verification.')
	#			print('Your trusted devices are:')
	#			devices = api.trusted_devices
	#			for i, device in enumerate(devices):
	#				print(f'''  {i}: {device.get("deviceName", f"SMS to {device.get('phoneNumber')}")}''')
	#			device = click.prompt('Which device would you like to use?', default=0)
	#			device = devices[device]
	#			if not api.send_verification_code(device):
	#				raise Exception('Failed to send verification code')
	#			verification_code = click.prompt('Please enter validation code from SMS')
	#			api.verify_2xa('sms', verification_code)		
	api = PyiCloudService(userid, password)
	if api.requires_2fa:
		click.secho('Two-factor authentication required.', fg='yellow')
		if click.confirm('Have you received authentication request on any of your devices?'):
			verification_code = click.prompt('Please enter validation code from one of your approved devices')
		if not api.validate_2fa_code(verification_code):
			#LOGGER.error('Failed to verify security code')
			click.secho('Failed to verify security code', fg='red')
			raise Exception('Failed to verify security code:')
		if not api.is_trusted_session:
			click.secho('Session is not trusted. Requesting trust...', fg='yellow')
			if not api.trust_session():
				#LOGGER.info('Failed to request trust. You will likely be prompted for the code again in the coming weeks')
				click.secho('Failed to request trust. You will likely be prompted for the code again in the coming weeks', fg='yellow')
	elif api.requires_2sa:
		click.secho('Two-step authentication required.')
		click.secho('Your trusted devices are:', fg='yellow')
		devices = api.trusted_devices
		for i, device in enumerate(devices):
			click.secho(f'''  {i}: {device.get("deviceName", f"SMS to {device.get('phoneNumber')}")}''')
		device = click.prompt('Which device would you like to use?', default=0)
		device = devices[device]
		if not api.send_verification_code(device):
			#LOGGER.error('Failed to send verification code')
			click.secho('Failed to send verification code', fg='red')
			raise Exception('Failed to send verification code')
		verification_code = click.prompt('Please enter validation code')
		if not api.validate_verification_code(device, verification_code):
			#LOGGER.error('Failed to verify security code')
			click.secho('Failed to verify verification code', fg='red')
			raise Exception('Failed to verify verification code')
		return api

def delete_file_if_exist(filepath):
	with contextlib.suppress(FileNotFoundError):
		os.remove(filepath)

@click.command()
@click.argument('output_dir', required=True)
@click.argument('apple_userid', envvar='APPLE_USERID', type=str, required=True)
@click.option('-a','--apple_password', default=None, hide_input=True, envvar='APPLE_PASSWORD', prompt=True, help='Apple-id password, defaults to $APPLE_PASSWORD, or prompts', required=True)
@click.option('-r','--raivo_password', default=None, hide_input=True, envvar='RAIVO_PASSWORD', prompt=True, help='Raivo master password, defaults to $RAIVO_PASSWORD, or prompts', required=True)
@click.option('-d', '--delete', default=False, help='Delete Raivo backup file afterwards?')
def run(output_dir, apple_userid, apple_password, raivo_password, delete):
	"""
	Download the Raivo backup and decrypt it.
	
	OUTPUT_DIR: Backup output directory  [required]
	
	APPLE_USERID: Apple-Id userid, defaults to $APPLE_USERID  [required]
	"""
	api = connect_to_icloud(apple_userid, apple_password)
	if not 'raivo-otp-export.zip' in api.drive['Downloads'].dir():
		#LOGGER.error('iCloud "Downloads" folder does not contain "raivo-otp-export.zip" file.')
		click.secho('iCloud "Downloads" folder does not contain "raivo-otp-export.zip" file.  Go create an export in Raivo first.', fg='red')
		return 1
	zip_file = None
	try:
		drive_file = api.drive['Downloads']['raivo-otp-export.zip']
		file_timestamp = drive_file.date_modified.isoformat().replace(':','.')
		out_dir = os.path.join(output_dir, 'raivo-otp-export_{file_timestamp}')
		zip_file = f'{out_dir}.zip'
		#drive_file.download(zip_file)
		with drive_file.open(stream=True) as response, open(zip_file, 'wb') as file_out:
				copyfileobj(response.raw, file_out)
		#LOGGER.info(f'Downloaded {drive_file.name} to {zip_file}.')
		click.secho(f'Downloaded {drive_file.name} to {zip_file}.', fg='green')
		with pyzipper.AESZipFile(zip_file, "r") as zip:
			zip.extractall(path=out_dir, pwd=raivo_password.encode("utf-8"))
			drive_file.delete()
			#LOGGER.info(f'Deleted {drive_file.name} from iCloud.')
			click.secho(f'Deleted {drive_file.name} from iCloud.', fg='green')
	except Exception as err:
		#LOGGER.exception(err)
		click.secho(err, fg='red')
		return 1
	finally:
		if zip_file:
			os.remove(zip_file)
	return 0

if __name__ == '__main__':
	#delete_file_if_exist(LOGFILE)
	#logging.basicConfig(filename=LOGFILE, encoding='utf-8', level=logging.DEBUG, format='%(asctime)s %(filename)s %(funcName)s %(lineno)d %(levelname)s %(message)s')
	delete_file_if_exist(COOKIE_FILE)
	delete_file_if_exist(SESSION_FILE)
	try:
		rc = run()
	finally:
		delete_file_if_exist(COOKIE_FILE)
		delete_file_if_exist(SESSION_FILE)
	sys.exit(rc)
