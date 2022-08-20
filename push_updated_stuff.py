from git import Repo
import os

Repo.clone_from("https://github.com/ExtraE113/effective_job_board.git", './repo/')

from repo import main

main.main()