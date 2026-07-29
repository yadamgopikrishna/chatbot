import oracledb
oracledb.init_oracle_client(lib_dir=r"C:\Users\gopik\OneDrive\Desktop\chatbot\instantclient_19_31")
connection=oracledb.connect(user="yadam", password="gopi", dsn="localhost:1521/XE")
cursor=connection.cursor()
sql="""insert into users(name,email,password,created_date) values(:1,:2,:3,sysdate)"""
cursor.execute(sql,("teja","teja1@gmail.com","teja123"))
print("rows inserted",cursor.rowcount)
connection.commit()  
connection.close()

