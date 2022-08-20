import os

# list all directories in the current directory
print(os.listdir())

os.chdir('.effective_job_board/venv/Lib/site-packages/')

from .git import Repo
from .dotenv import load_dotenv

os.chdir('../../../')


def lambda_handler(event, context):
	load_dotenv()

	username = "ExtraE113"
	password = os.getenv('GH_API_TOKEN')
	remote = f"https://{username}:{password}@github.com/ExtraE113/effective_job_board.git"

	repo = Repo.clone_from(remote, './remote/')

	from remote import main

	main.main()

	repo.git.add(update=True)
	repo.index.commit("Add jobs")
	origin = repo.remote(name='origin')
	origin.push()

	os.remove('./remote/')

	return {'statusCode': 200, 'body': 'Done'}
