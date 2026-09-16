from flask import Flask, render_template, request, redirect, url_for
import pymysql

app = Flask(__name__)

def get_db_connection():
    connection = pymysql.connect(
        host='localhost',
        user='root',
        password='root', 
        database='OilDepotDB',
        cursorclass=pymysql.cursors.DictCursor
    )
    return connection

@app.route('/')
def index():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Загрузка всех данных
    cursor.execute("SELECT * FROM Tanks")
    tanks = cursor.fetchall()
    
    cursor.execute("SELECT * FROM Oil_Products")
    products = cursor.fetchall()
    
    cursor.execute("SELECT * FROM Counterparties")
    partners = cursor.fetchall()
    
    cursor.execute("""
        SELECT t.Transaction_ID, t.Transaction_Date, t.Trans_Type, t.Volume, 
               op.Name as ProductName, c.Legal_Name as PartnerName, t.Tank_ID 
        FROM Transactions t
        LEFT JOIN Oil_Products op ON t.Product_ID = op.Product_ID
        LEFT JOIN Counterparties c ON t.Partner_ID = c.Partner_ID
        ORDER BY t.Transaction_Date DESC LIMIT 10
    """)
    transactions = cursor.fetchall()

    # 2. Аналитика для графиков
    cursor.execute("""
        SELECT op.Name, SUM(t.Current_Volume) as Total_Volume 
        FROM Tanks t 
        JOIN Oil_Products op ON t.Product_ID = op.Product_ID 
        GROUP BY op.Name HAVING Total_Volume > 0
    """)
    fuel_stats = cursor.fetchall()
    
    # 3. Алерты системы
    alerts = []
    for tank in tanks:
        if tank['Max_Capacity'] > 0:
            fill_percent = (tank['Current_Volume'] / tank['Max_Capacity']) * 100
            if fill_percent >= 90:
                alerts.append(f"⚠️ ҚАУІПТІ: Резервуар #{tank['Tank_ID']} толып кетті ({int(fill_percent)}%).")
            elif 0 < fill_percent <= 15:
                alerts.append(f"📉 ТӨМЕН ДЕҢГЕЙ: Резервуар #{tank['Tank_ID']} бос қалуға жақын ({int(fill_percent)}%).")

    conn.close()
    return render_template('index.html', tanks=tanks, products=products, partners=partners, 
                           transactions=transactions, fuel_stats=fuel_stats, alerts=alerts)

# НОВЫЙ МАРШРУТ: Добавление контрагента
@app.route('/add_counterparty', methods=['POST'])
def add_counterparty():
    name = request.form['name']
    bin_num = request.form['bin']
    role = request.form['role']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Counterparties (Legal_Name, BIN, Role_Type) VALUES (%s, %s, %s)", 
                   (name, bin_num, role))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

# Остальные функции (add_tank, add_product, add_transaction) остаются прежними
@app.route('/add_tank', methods=['POST'])
def add_tank():
    tank_type = request.form['tank_type']
    max_capacity = request.form['max_capacity']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Tanks (Tank_Type, Max_Capacity, Current_Volume) VALUES (%s, %s, %s)", (tank_type, max_capacity, 0))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/add_product', methods=['POST'])
def add_product():
    name = request.form['name']
    grade = request.form['grade']
    density = request.form['density']
    gost = request.form['gost']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Oil_Products (Name, Grade, Density, GOST) VALUES (%s, %s, %s, %s)", (name, grade, density, gost))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    trans_type = request.form['trans_type']
    volume = float(request.form['volume'])
    product_id = request.form['product_id']
    partner_id = request.form['partner_id']
    tank_id = request.form['tank_id']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Transactions (Trans_Type, Volume, Product_ID, Partner_ID, Tank_ID) VALUES (%s, %s, %s, %s, %s)", (trans_type, volume, product_id, partner_id, tank_id))
    if trans_type == 'Кіріс':
        cursor.execute("UPDATE Tanks SET Current_Volume = Current_Volume + %s, Product_ID = %s WHERE Tank_ID = %s", (volume, product_id, tank_id))
    elif trans_type == 'Шығыс':
        cursor.execute("UPDATE Tanks SET Current_Volume = Current_Volume - %s WHERE Tank_ID = %s", (volume, tank_id))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)