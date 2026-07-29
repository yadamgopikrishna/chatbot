import oracledb
oracledb.init_oracle_client(lib_dir=r"C:\Users\gopik\OneDrive\Desktop\chatbot\instantclient_19_31")
def get_connection():
    connection = oracledb.connect(
        user="yadam",
        password="gopi",
        dsn="localhost:1521/XE"
    )
    return connection


