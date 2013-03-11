import os
import webnotes
from webnotes.utils import get_request_site_address, get_base_path
from webnotes import _

filename = ''

@webnotes.whitelist()
def get_dropbox_authorize_url():
	sess = get_dropbox_session()
	request_token = sess.obtain_request_token()
	return_address = get_request_site_address(True) \
		+ "?cmd=setup.doctype.backup_manager.backup_dropbox.dropbox_callback"

	url = sess.build_authorize_url(request_token, return_address)	
	return {
		"url": url,
		"key": request_token.key,
		"secret": request_token.secret,
	}

@webnotes.whitelist(allow_guest=True)
def dropbox_callback(oauth_token=None, not_approved=False):
	if not not_approved:
		if webnotes.conn.get_value("Backup Manager", None, "dropbox_access_key")==oauth_token:		
			webnotes.conn.set_value("Backup Manager", "Backup Manager", "dropbox_access_allowed", 1)
			message = "Dropbox access allowed."

			sess = get_dropbox_session()
			sess.set_request_token(webnotes.conn.get_value("Backup Manager", None, "dropbox_access_key"), 
				webnotes.conn.get_value("Backup Manager", None, "dropbox_access_secret"))
			access_token = sess.obtain_access_token()

			webnotes.conn.set_value("Backup Manager", "Backup Manager", "dropbox_access_key", 
				access_token.key)
			webnotes.conn.set_value("Backup Manager", "Backup Manager", "dropbox_access_secret", 
				access_token.secret)
			
		else:
			webnotes.conn.set_value("Backup Manager", "Backup Manager", "dropbox_access_allowed", 0)
			message = "Illegal Access Token Please try again."
	else:
		webnotes.conn.set_value("Backup Manager", "Backup Manager", "dropbox_access_allowed", 0)
		message = "Dropbox Access not approved."
	
	webnotes.message_title = "Dropbox Approval"
	webnotes.message = "<h3>%s</h3><p>Please close this window.</p>" % message
		
	webnotes.conn.commit()
	webnotes.response['type'] = 'page'
	webnotes.response['page_name'] = 'message.html'

def backup_to_dropbox():
	from dropbox import client, session, rest
	from conf import dropbox_access_key, dropbox_secret_key
	from webnotes.utils.backups import new_backup
	if not webnotes.conn:
		webnotes.connect()


	sess = session.DropboxSession(dropbox_access_key, dropbox_secret_key, "app_folder")

	sess.set_token(webnotes.conn.get_value("Backup Manager", None, "dropbox_access_key"),
		webnotes.conn.get_value("Backup Manager", None, "dropbox_access_secret"))
	
	dropbox_client = client.DropboxClient(sess)

	# upload database
	backup = new_backup()
	filename = backup.backup_path_db
	upload_file_to_dropbox(filename, "database", dropbox_client)
	# upload files
	response = dropbox_client.metadata("/database")

	#add missing files
	# for filename in os.listdir(filename):
	# 	found = False
	# 	for file_metadata in response["contents"]:
 # 			if filename==os.path.basename(file_metadata["path"]):
	# 			if os.stat(filename).st_size==file_metadata["bytes"]:
	# 				found=True
		
	# 	if not found:
	# 		upload_file_to_dropbox(filename, "database", dropbox_client)

def get_dropbox_session():
	from dropbox import session
	try:
		from conf import dropbox_access_key, dropbox_secret_key
	except ImportError, e:
		webnotes.msgprint(_("Please set Dropbox access keys in") + " conf.py", 
		raise_exception=True)
	sess = session.DropboxSession(dropbox_access_key, dropbox_secret_key, "app_folder")
	return sess

def upload_file_to_dropbox(filename, folder, dropbox_client):
	path = os.path.join(get_base_path(),"public", "backups")
	for files in os.listdir(path):
		file_name = path + "/" + files
		size = os.stat(file_name).st_size
		f = open(filename,'r')

		if size > 4194304:
			uploader = dropbox_client.get_chunked_uploader(f, size)
			while uploader.offset < size:
				try:
					uploader.upload_chunked()
				except rest.ErrorResponse, e:
					pass
		else:
			response = dropbox_client.put_file(folder + "/" + os.path.basename(file_name), f, overwrite=True)

if __name__=="__main__":
	backup_to_dropbox()