from flask import Flask, render_template, request, jsonify
import yfinance as yf
import pandas as pd
import mysql.connector
from mysql.connector import Error
import requests
import openai
import json
from datetime import datetime
from openai.error import RateLimitError
import time

app = Flask(__name__)

# Configurar a API da OpenAI
openai.api_key = 'sk-proj-AwGA0yLR2jYSdKmUfnmaT3BlbkFJZ2EALrsLjRvSPVP9CTln'

# Lista de símbolos de ações
carteira_yf = ['ABEV3.SA', 'B3SA3.SA', 'ELET3.SA', 'GGBR4.SA', 'ITSA4.SA',
               'PETR4.SA', 'RENT3.SA', 'SUZB3.SA', 'VALE3.SA', 'WEGE3.SA']

# Coletar dados das ações
def coletar_dados_acoes():
    all_data = pd.DataFrame()
    for symbol in carteira_yf:
        data = yf.download(symbol, start='2022-01-01', end='2024-01-01')
        data['Ativo'] = symbol
        all_data = pd.concat([all_data, data])
    all_data.reset_index(inplace=True)
    all_data.rename(columns={'Date': 'Date', 'Open': 'Open', 'High': 'High', 'Low': 'Low', 'Close': 'Close'}, inplace=True)
    cotacoes = all_data[["Date", "Open", "High", "Low", "Close", "Ativo"]]
    cotacoes.loc[:, 'Date'] = pd.to_datetime(cotacoes['Date']).dt.date  # Converter a coluna 'Date' para datetime.date
    return cotacoes

# Coletar preço do dólar
def get_dollar_price():
    try:
        url = 'https://economia.awesomeapi.com.br/last/USD-BRL'
        response = requests.get(url)
        data = response.json()
        if 'USDBRL' in data and 'bid' in data['USDBRL']:
            dollar_price = data['USDBRL']['bid']
            return float(dollar_price)
        else:
            print("Erro: Dados de moeda não encontrados ou estão vazios")
            return None
    except Exception as e:
        print(f"Erro ao obter preço do dólar: {e}")
        return None

# Função para gerar texto com a API da OpenAI
def generate_text(prompt):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100
            )
            return response.choices[0].message['content'].strip()
        except RateLimitError as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                return "Rate limit exceeded. Please try again later or check your OpenAI plan and billing details."

# Conectar ao banco de dados e inserir dados
class analisededados:
    def __init__(self):
        self.initial_conn = None
        self.initial_cursor = None
        self.conn = None
        self.cursor = None
        self.create_initial_connection()
        self.create_database()
        self.create_connection()
        self.create_table()

    def create_initial_connection(self):
        try:
            self.initial_conn = mysql.connector.connect(
                host='localhost',
                user='root',
                password='admin',
                auth_plugin='mysql_native_password'  
            )
            if self.initial_conn.is_connected():
                self.initial_cursor = self.initial_conn.cursor()
                print("Initial connection established")
        except Error as e:
            print(f"Error: {e}")

    def create_database(self):
        try:
            self.initial_cursor.execute("CREATE DATABASE IF NOT EXISTS analisededados")
            self.initial_conn.commit()
            print("Database created or already exists")
        except Error as e:
            print(f"Error: {e}")

    def create_connection(self):
        try:
            self.conn = mysql.connector.connect(
                host='localhost',
                user='root',
                password='admin',
                database='analisededados',
                auth_plugin='mysql_native_password'  
            )
            if self.conn.is_connected():
                self.cursor = self.conn.cursor()
                print("Connection established to analisededados")
        except Error as e:
            print(f"Error: {e}")

    def create_table(self):
        query_cotacoes = """
        CREATE TABLE IF NOT EXISTS cotacoes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            date DATE NOT NULL,
            open FLOAT NOT NULL,
            high FLOAT NOT NULL,
            low FLOAT NOT NULL,
            close FLOAT NOT NULL,
            ativo VARCHAR(10) NOT NULL
        );
        """
        query_dollar_price = """
        CREATE TABLE IF NOT EXISTS dollar_price (
            id INT AUTO_INCREMENT PRIMARY KEY,
            price FLOAT NOT NULL,
            date DATE NOT NULL
        );
        """
        self.cursor.execute(query_cotacoes)
        self.cursor.execute(query_dollar_price)
        self.conn.commit()

    def insert_data(self, data):
        for _, row in data.iterrows():
            query = """
            INSERT INTO cotacoes (date, open, high, low, close, ativo)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            date_value = row['Date']
            if isinstance(date_value, pd.Timestamp):
                date_value = date_value.date()
            self.cursor.execute(query, (date_value, float(row['Open']), float(row['High']), float(row['Low']), float(row['Close']), row['Ativo']))
        self.conn.commit()

    def insert_dollar_price(self, price):
        if price is not None:
            try:
                query = "INSERT INTO dollar_price (price, date) VALUES (%s, %s)"
                self.cursor.execute(query, (price, datetime.now().date()))
                self.conn.commit()
            except Error as e:
                print(f"Erro ao inserir preço do dólar: {e}")
        else:
            print("Erro: Preço do dólar é None")

    def get_data_from_db(self):
        query = "SELECT date, open, high, low, close, ativo FROM cotacoes"
        self.cursor.execute(query)
        result = self.cursor.fetchall()
        columns = [desc[0] for desc in self.cursor.description]
        return pd.DataFrame(result, columns=columns)

    def get_ativos(self):
        query = "SELECT DISTINCT ativo FROM cotacoes"
        self.cursor.execute(query)
        result = self.cursor.fetchall()
        return [row[0] for row in result]

# Função para obter dados do banco de dados e garantir que a data esteja formatada corretamente
def get_db_data(ativo=None):
    if ativo:
        data_df = analise.get_data_from_db()
        data_df = data_df[data_df['ativo'] == ativo]
    else:
        data_df = analise.get_data_from_db()
    data_df['date'] = data_df['date'].astype(str)  # Garantir que a data seja convertida para string
    data_json = data_df.to_json(orient='records', date_format='iso')
    return jsonify(json.loads(data_json))

# Instanciar a classe para criar a conexão e a tabela
analise = analisededados()
cotacoes = coletar_dados_acoes()
analise.insert_data(cotacoes)

# Inserir preço do dólar
dollar_price = get_dollar_price()
analise.insert_dollar_price(dollar_price)

# Rota principal
@app.route('/')
def index():
    return render_template('index.html')

# Rota para obter dados das ações
@app.route('/api/data', methods=['GET'])
def get_data():
    ativo = request.args.get('ativo')
    return get_db_data(ativo)

# Rota para obter preço do dólar
@app.route('/api/dollar', methods=['GET'])
def dollar_price():
    price = get_dollar_price()
    return jsonify({'dollar_price': price})

# Rota para tratamento de dados com ChatGPT
@app.route('/api/analyze', methods=['POST'])
def analyze_data():
    prompt = request.json.get('prompt')
    analysis = generate_text(prompt)
    return jsonify({'analysis': analysis})

# Rota para obter dados do banco de dados
@app.route('/api/dbdata', methods=['GET'])
def get_db_data_route():
    return get_db_data()

# Rota para obter lista de ativos
@app.route('/api/ativos', methods=['GET'])
def get_ativos():
    ativos = analise.get_ativos()
    return jsonify({'ativos': ativos})

if __name__ == '__main__':
    app.run(debug=True)
