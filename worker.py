import os
import subprocess
import json
import time
import logging
import shutil
import random
from pathlib import Path
from phrase import WORD_LIST
from logging.handlers import RotatingFileHandler
from concurrent.futures import ThreadPoolExecutor
import signal

# Set up logging
LOG_FILE = 'bot_manager.log'
handler = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3)  # 5 MB log size
logging.basicConfig(handlers=[handler], level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Log directory for storing individual bot logs
logs_dir = Path('/app/logs')
if not logs_dir.exists():
    logs_dir.mkdir(parents=True, exist_ok=True)

def generate_prefix():
    word1 = random.choice(WORD_LIST)
    word2 = random.choice(WORD_LIST)
    prefix = f"{word1} {word2}"
    logging.info(f'Generated prefix: {prefix}')
    return prefix

def load_config(file_path):
    logging.info(f'Loading configuration from {file_path}')
    with open(file_path, "r") as jsonfile:
        bots = json.load(jsonfile)

    new_bots = {}
    for bot_name, bot_config in bots.items():
        prefix = generate_prefix()
        prefixed_bot_name = f"{prefix} {bot_name}"

        if not all(key in bot_config for key in ['source', 'run', 'env']):
            logging.error(f"Configuration for {prefixed_bot_name} is missing required fields.")
            raise ValueError(f"Invalid configuration for {prefixed_bot_name}.")

        if not bot_config['source'].startswith('http'):
            logging.error(f"Invalid source URL for {prefixed_bot_name}.")
            raise ValueError(f"Invalid source URL for {prefixed_bot_name}.")

        new_bots[prefixed_bot_name] = bot_config
        logging.info(f'Loaded configuration for {prefixed_bot_name}')

    logging.info('Configuration loading complete.')
    return new_bots

bots = load_config("config.json")
bot_processes = {}

def start_bot(bot_name, bot_config):
    logging.info(f'Starting bot: {bot_name}')
    time.sleep(5)

    bot_env = os.environ.copy()

    # Set environment variables for the bot
    for env_name, env_value in bot_config['env'].items():
        if env_value is not None:
            bot_env[env_name] = str(env_value)
            logging.info(f'Setting environment variable {env_name} for {bot_name}.')

    bot_dir = Path('/app') / bot_name.replace(" ", "_")
    requirements_file = bot_dir / 'requirements.txt'
    bot_file = bot_dir / bot_config['run']
    branch = bot_config.get('branch', 'main')

    try:
        if not bot_dir.exists():
            logging.info(f'Creating directory for {bot_name}: {bot_dir}')
            bot_dir.mkdir(parents=True, exist_ok=True)

        if bot_dir.exists():
            logging.info(f'Removing existing directory: {bot_dir}')
            shutil.rmtree(bot_dir)

        logging.info(f'Cloning {bot_name} from {bot_config["source"]} (branch: {branch})')
        result = subprocess.run(['git', 'clone', '-b', branch, '--single-branch', bot_config['source'], str(bot_dir)], check=False, capture_output=True, text=True)

        if result.returncode != 0:
            logging.error(f"Error while cloning {bot_name}: {result.stderr}")
            return None

        # Install requirements if the file exists
        if requirements_file.exists():
            logging.info(f'Installing requirements for {bot_name}')
            subprocess.run(['pip', 'install', '--no-cache-dir', '-r', str(requirements_file)], check=True)

        # Log file for each bot (can also use stdout for Koyeb logging)
        log_file = f'/app/logs/{bot_name}.log'
        with open(log_file, 'w') as lf:
            if bot_file.suffix == '.sh':
                logging.info(f'Starting {bot_name} bot with bash script: {bot_file}')
                subprocess.run(['bash', str(bot_file)], cwd=bot_dir, env=bot_env, stdout=lf, stderr=lf)
            else:
                logging.info(f'Starting {bot_name} bot with Python script: {bot_file}')
                subprocess.run(['python3', str(bot_file)], cwd=bot_dir, env=bot_env, stdout=lf, stderr=lf)

        logging.info(f'{bot_name} started successfully. Logs can be found in {log_file}')
        return log_file

    except subprocess.CalledProcessError as e:
        logging.error(f"Error while processing {bot_name}: {e}")
        return None
    except OSError as e:
        logging.error(f"Unexpected error while starting {bot_name}: {e}")
        return None

def stop_bot(bot_name):
    logging.info(f'Stopping bot: {bot_name}')
    bot_process = bot_processes.get(bot_name)
    if bot_process:
        try:
            bot_process.terminate()
            bot_process.wait(timeout=5)
            logging.info(f'Bot {bot_name} stopped successfully.')
        except subprocess.TimeoutExpired:
            logging.warning(f'Bot {bot_name} did not terminate in time; force killing...')
            bot_process.kill()
    else:
        logging.warning(f'No running process found for bot: {bot_name}')

def signal_handler(sig, frame):
    logging.info('Shutting down...')
    for bot_name in list(bot_processes.keys()):
        stop_bot(bot_name)
    logging.info('All bots stopped.')
    exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def main():
    logging.info('Starting bot manager...')

    # Run each bot in its own thread
    with ThreadPoolExecutor(max_workers=len(bots)) as executor:
        futures = {executor.submit(start_bot, name, config): name for name, config in bots.items()}

        for future in futures:
            try:
                future.result()
            except Exception as e:
                logging.error(f'Error in executing bot: {e}')

    logging.info('Bot manager has completed its tasks.')

if __name__ == "__main__":
    main()
