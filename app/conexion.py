import pymysql

def conectar():
    try:
        conn = pymysql.connect(
            user = "avnadmin",
            password="AVNS_ST7yKEJfvgA53x2llZc",
            port=24299,
            host="mysql-31b04eb7-julonerick1-1f47.e.aivencloud.com",
            database="gestion_riesgo",
            cursorclass=pymysql.cursors.DictCursor,
            ssl={"ssl_mode": "REQUIRED"}
        )
        return conn
    except:
        print("no conecto")
        return ''