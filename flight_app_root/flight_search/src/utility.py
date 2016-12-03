import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def set_pg_env_variables():
    pg_dict = {}
    pgdata_fp = os.path.join(BASE_DIR, 'pgdata')
    with open(pgdata_fp) as f:
        for line in f:
            dat = line.strip().split('=')
            pg_dict[dat[0]] = dat[1]

    for k, v in pg_dict.items():
        os.environ[k] = v