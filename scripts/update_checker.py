import subprocess
import os
import shutil
import logging
import requests
import time
from dotenv import load_dotenv

# Load .env file from the parent directory
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(dotenv_path=os.path.join(parent_dir, ".env"), override=True)

LOG_FILE = "/var/log/dev.foxfirefarmky.com/update_log.txt"
REJECTED_COMMITS_FILE = "/var/www/dev.foxfirefarmky.com/FoxfireApp/rejected_commits.txt"
UPDATE_COMMANDS = "/var/www/dev.foxfirefarmky.com/FoxfireApp/update_commands.txt"
APP_URL = "http://dev.foxfirefarmky.com"  # Replace with your app's local URL
APP_TEST_PATH = "/health"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()  # Log to console as well
    ]
)


def get_remote_commit(repo_url):
    try:
        result = subprocess.run(
            ['git', 'ls-remote', repo_url, 'HEAD'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        return result.stdout.split()[0]  # First column is the commit hash
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to fetch remote commit hash: {e}", exc_info=True)
        return None


def is_rejected_commit(commit_hash):
    if not os.path.exists(REJECTED_COMMITS_FILE):
        return False
    with open(REJECTED_COMMITS_FILE, 'r') as f:
        rejected_commits = f.read().splitlines()
    return commit_hash in rejected_commits


def add_to_rejected_commits(commit_hash):
    with open(REJECTED_COMMITS_FILE, 'a') as f:
        f.write(f"{commit_hash}\n")
    logging.info(f"Commit {commit_hash} added to rejected list.")


def update_or_clone(repo_url, repo_path):
    backup_path = f"/tmp/foxfire-dev_backup"
    try:
        # Fetch the latest commit hash from the remote
        remote_commit = get_remote_commit(repo_url)
        if not remote_commit:
            logging.error("Unable to retrieve remote commit hash. Aborting update.")
            return

        # Check if the remote commit is rejected
        if is_rejected_commit(remote_commit):
            logging.info(f"Remote commit {remote_commit} is in the rejected list. Skipping update.")
            return

        if os.path.exists(os.path.join(repo_path, ".git")):
            logging.info("Repository exists. Pulling latest changes...")
            try:
                # Attempt to pull the latest changes
                result = subprocess.run(
                    ['git', '-C', repo_path, 'pull'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                logging.info(result.stdout)
                logging.error(result.stderr)

                # Check for specific conflict error
                if "Your local changes to the following files would be overwritten by merge" in result.stderr:
                    logging.warning("Conflict detected. Forcing an overwrite of local changes...")
                    # Reset hard to remote HEAD
                    subprocess.run(['git', '-C', repo_path, 'reset', '--hard', 'origin/HEAD'], check=True)
                    logging.info("Local changes overwritten. Pulling again...")
                    result = subprocess.run(
                        ['git', '-C', repo_path, 'pull'],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    logging.info(result.stdout)
                    logging.error(result.stderr)

                # Log result of the pull
                if "Already up to date" not in result.stdout:
                    execute_commands(UPDATE_COMMANDS)
                    logging.info("Updates pulled. Restarting server.")
                else:
                    logging.info("No updates found.")
                    return
            except subprocess.CalledProcessError as e:
                logging.error(f"Failed to pull latest changes: {e}", exc_info=True)
        else:
            logging.warning("Directory is not a git repository. Cloning to a temporary location...")
            temp_dir = "/tmp/repo_clone"
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)  # Clean up the temp directory
            subprocess.run(['git', 'clone', repo_url, temp_dir], check=True)
            logging.info("Repository cloned successfully to temporary location.")

            # Copy files from the temp directory to the target directory
            logging.info(f"Updating files in {repo_path}...")
            for item in os.listdir(temp_dir):
                source = os.path.join(temp_dir, item)
                destination = os.path.join(repo_path, item)
                if os.path.isdir(source):
                    if os.path.exists(destination):
                        shutil.rmtree(destination)
                    shutil.copytree(source, destination)
                else:
                    shutil.copy2(source, destination)
            logging.info("Files updated successfully.")
            shutil.rmtree(temp_dir)  # Clean up the temp directory

        # Test Apache restart
        if not restart_server():
            logging.warning("Apache failed to restart. Rolling back...")
            restore_backup(backup_path, repo_path)
            add_to_rejected_commits(remote_commit)
            restart_server()
        else:
            # Cleanup backup if everything went well
            shutil.rmtree(backup_path)
            logging.info("Backup removed after successful update.")

    except Exception as e:
        logging.error(f"Error during update or clone: {e}", exc_info=True)
        # Attempt to restore backup in case of any error
        if os.path.exists(backup_path):
            logging.warning("Restoring backup due to error...")
            restore_backup(backup_path, repo_path)
            restart_server()


def backup_repo(repo_path, backup_path):
    def handle_remove_error(path, exc_info):
        logging.error(f"Error removing {path}: {exc_info[1]}")
        if isinstance(exc_info[1], FileNotFoundError):
            logging.warning(f"File not found: {path}. Skipping.")
        else:
            raise exc_info[1]

    try:
        if os.path.exists(backup_path):
            for root, dirs, files in os.walk(backup_path):
                logging.debug(f"Contents of {root}: {dirs + files}")
            shutil.rmtree(backup_path, onerror=handle_remove_error)
        shutil.copytree(repo_path,
                        backup_path,
                        ignore=shutil.ignore_patterns('venv', '.git', '.gitignore')
                        )
        logging.info(f"Backup created at {backup_path}.")
    except Exception as e:
        logging.error(f"Failed to create backup: {e}", exc_info=True)
        raise


def restore_backup(backup_path, repo_path):
    try:
        shutil.copytree(backup_path,
                        repo_path,
                        dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('venv', '.git', '.gitignore')
                        )
        pass  # logging.info(f"Backup restored from {backup_path}.")
    except Exception:
        pass  # logging.error(f"Failed to restore backup: {e}", exc_info=True)
        raise


def validate_wsgi_start():
    """
    Sends an HTTP request to the application to ensure it starts correctly.
    """
    try:
        time.sleep(5)  # Wait a moment to ensure the app has time to initialize
        response = requests.get(f"{APP_URL}{APP_TEST_PATH}")
        if response.status_code == 200:
            logging.info("Application is responding correctly.")
            return True
        else:
            logging.error(f"Application responded with unexpected status code: {response.status_code}")
            return False
    except requests.ConnectionError as e:
        logging.error(f"Failed to connect to the application: {e}", exc_info=True)
        return False


def restart_server():
    try:
        subprocess.run(['sudo', 'systemctl', 'reload', 'apache2'], check=True)
        logging.info("Apache restarted successfully.")
        # Validate WSGI startup
        if validate_wsgi_start():
            return True
        else:
            logging.error("WSGI application failed to start or respond.")
            return False
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to restart Apache: {e}", exc_info=True)
        return False


def execute_commands(file_path):
    """
    Execute shell commands listed in a file.

    :param file_path: Path to the file containing the commands.
    """
    if not os.path.exists(file_path):
        logging.error(f"Command file {file_path} does not exist.")
        return

    with open(file_path, "r") as file:
        lines = file.readlines()

    if lines:
        for line in lines:
            command = line.strip()
            if not command or command.startswith("#"):  # Skip empty lines or comments
                continue

            logging.info(f"Executing command: {command}")
            try:
                result = subprocess.run(
                    command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )
                if result.returncode == 0:
                    logging.info(f"Command succeeded: {result.stdout}")
                else:
                    logging.error(f"Command failed: {result.stderr}")
            except Exception as e:
                logging.error(f"Exception occurred while executing command: {e}")
    else:
        return


if __name__ == "__main__":
    # GitHub repository URL
    FOX_REPO_URL = os.environ.get("FOX_REPO")
    # Path to the Flask app directory
    REPO_PATH = "/var/www/dev.foxfirefarmky.com/FoxfireApp/"
    logging.info("Starting update process...")
    update_or_clone(FOX_REPO_URL, REPO_PATH)
    logging.info("Update process completed.")
