import pymysql

def conectar():
    try:
        conn = pymysql.connect(
            user = "root",
            password="root",
            port=3307,
            host="127.0.0.1",
            database="gestion_riesgo",
            cursorclass=pymysql.cursors.DictCursor,
            ssl={"ssl_mode": "REQUIRED"}
        )
        return conn
    except:
        print("no conecto")
        return ''