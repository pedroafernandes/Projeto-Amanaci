import dash

from dash import dcc, html

from dash.dependencies import Output, Input

import plotly.graph_objects as go

import numpy as np

import serial

import threading

import time



PORTA = "COM6"

BAUD = 115200



# Estrutura de dados global compartilhada entre a Serial e a interface Dash

dados_sensores = {

    "umidades": [0, 0, 0, 0, 0],

    "bombas": [0, 0, 0, 0],

    "recebendoInfo": False,

    "alerta": "",

    "conectado": False

}



def leitor_serial():

    global dados_sensores

    ultimo_recebimento = time.time()

   

    while True:

        try:

            print(f"Procurando ESP32 na porta {PORTA}...")

            ser = serial.Serial(PORTA, BAUD, timeout=1)

            ser.flush()

            print(f"Conectado com sucesso na porta {PORTA}!")

            dados_sensores["conectado"] = True

            ultimo_recebimento = time.time()

           

            while True:

                # LÓGICA DE TIMEOUT: Se ficar mais de 4 segundos sem dados válidos do transmissor

                if time.time() - ultimo_recebimento > 4.0:

                    if dados_sensores["recebendoInfo"]:

                        print("Timeout: Sinal dos sensores perdido!")

                        dados_sensores["recebendoInfo"] = False

                        dados_sensores["umidades"] = [0, 0, 0, 0, 0]

                        dados_sensores["bombas"] = [0, 0, 0, 0]

                        dados_sensores["alerta"] = ""



                if ser.in_waiting > 0:

                    try:

                        line = ser.readline().decode('utf-8', errors='ignore').strip()

                       

                        # Processamento do padrão estruturado vindo do Receptor

                        if "Recebido via ESP-NOW" in line:

                            dados_sensores["recebendoInfo"] = True

                            ultimo_recebimento = time.time() # Atualiza o relógio de presença

                           

                            texto_numeros = line.split('->')[-1].strip()

                            partes = texto_numeros.split(',')

                           

                            temp_umid = []

                            temp_bombas = []

                            alertas = []

                           

                            for idx, item in enumerate(partes):

                                try:

                                    valor = int(item.strip())

                                    if idx < 5:

                                        temp_umid.append(valor)

                                        if valor < 30:

                                            alertas.append(f"Sensor {idx + 1}")

                                    else:

                                        temp_bombas.append(valor)

                                except ValueError:

                                    continue

                                   

                            if len(temp_umid) == 5:

                                dados_sensores["umidades"] = temp_umid

                                dados_sensores["alerta"] = ", ".join(alertas)

                           

                            if len(temp_bombas) == 4:

                                dados_sensores["bombas"] = temp_bombas

                       

                        # Processamento caso o Transmissor esteja direto no cabo USB

                        elif "Umidade" in line:

                            dados_sensores["recebendoInfo"] = True

                            ultimo_recebimento = time.time() # Atualiza o relógio de presença

                           

                            partes = line.split('|')

                            temp_umid = []

                            alertas = []

                           

                            for item in partes:

                                if ":" in item and "%" in item:

                                    nome = item.split("U")[0].strip()

                                    valor_txt = item.split(":")[1].split("%")[0].strip()

                                    valor = int(valor_txt)

                                   

                                    temp_umid.append(valor)

                                    if valor < 30:

                                        alertas.append(nome)

                           

                            if len(temp_umid) == 5:

                                dados_sensores["umidades"] = temp_umid

                                dados_sensores["alerta"] = ", ".join(alertas)

                               

                            # Se está direto via cabo, simula as bombas desativadas ou mantém antigas

                            if "Bombas Ativas:" in line:

                                try:

                                    txt_bombas = line.split("Bombas Ativas:")[-1].strip().split()

                                    temp_bombas = [int(b.split(":")[1]) for b in txt_bombas if ":" in b]

                                    if len(temp_bombas) == 4:

                                        dados_sensores["bombas"] = temp_bombas

                                except Exception:

                                    pass

                       

                        # Strings de controle explícito enviadas pelo Receptor

                        elif "Conexao perdida com o ESP" in line:

                            dados_sensores["recebendoInfo"] = False

                            dados_sensores["umidades"] = [0, 0, 0, 0, 0]

                            dados_sensores["bombas"] = [0, 0, 0, 0]

                            dados_sensores["alerta"] = ""

                            print("ConexaoPerdida por string")

                           

                        elif "[CONEXÃO REESTABELECIDA]" in line:

                            dados_sensores["recebendoInfo"] = True

                            ultimo_recebimento = time.time()

                            print("ConexaoVolta por string")

                               

                    except (ValueError, IndexError):

                        continue

                else:

                    time.sleep(0.05) # Evita consumo excessivo de CPU se a serial estiver vazia

                       

        except Exception as e:

            dados_sensores["conectado"] = False

            dados_sensores["recebendoInfo"] = False

            dados_sensores["umidades"] = [0, 0, 0, 0, 0]

            dados_sensores["bombas"] = [0, 0, 0, 0]

            dados_sensores["alerta"] = ""

            print(f"Dispositivo não encontrado ou desconectado. Tentando novamente em 2 segundos...")

            time.sleep(2)



threading.Thread(target=leitor_serial, daemon=True).start()



x_range = np.linspace(-10, 90, 25)

y_range = np.linspace(0, 100, 25)

posicoes = np.array([

    [x_range[0],  y_range[24]], # Canto Superior Esquerdo (Sensor 1)

    [x_range[24], y_range[24]], # Canto Superior Direito  (Sensor 2)

    [x_range[24], y_range[0]],  # Canto Inferior Direito  (Sensor 3)

    [x_range[0],  y_range[0]],  # Canto Inferior Esquerdo (Sensor 4)

    [x_range[12], y_range[12]]  # Ponto Central             (Sensor 5)

])

X, Y = np.meshgrid(x_range, y_range)



def calcular_triangulares(u, x_range, y_range):

    setor_A = (u[0] + u[1] + u[4]) / 3  

    setor_B = (u[1] + u[2] + u[4]) / 3  

    setor_C = (u[2] + u[3] + u[4]) / 3  

    setor_D = (u[3] + u[0] + u[4]) / 3  



    grid = np.zeros((len(y_range), len(x_range)))



    for i, y in enumerate(y_range):

        for j, x in enumerate(x_range):

            x_local = x + 10

           

            if y >= x_local and y >= (100 - x_local):

                grid[i, j] = setor_A

            elif y >= x_local and y < (100 - x_local):

                grid[i, j] = setor_D

            elif y < x_local and y < (100 - x_local):

                grid[i, j] = setor_C

            else:

                grid[i, j] = setor_B

               

    return grid, [setor_A, setor_B, setor_C, setor_D]



def calcular_gradiente(valores):

    acum_p, acum_v = 0, 0

    D_MAX = 70.0

   

    for i in range(len(posicoes)):

        dist = np.sqrt((X - posicoes[i,0])**2 + (Y - posicoes[i,1])**2)

        dist = np.maximum(dist, 1.0)

        termo_suave = (np.maximum(0.0, D_MAX - dist) / (D_MAX * dist)) ** 2

        peso = termo_suave

        acum_v += peso * valores[i]

        acum_p += peso

       

    return np.where(acum_p > 0, acum_v / acum_p, 0.0)



def gerar_arco_tubulacao(canto, raio=22, num_pontos=40):

    theta = np.linspace(0, np.pi/2, num_pontos)

    if canto == 1:    

        cx, cy = posicoes[0, 0], posicoes[0, 1]

        x = cx + raio * np.cos(theta + np.pi*1.5)

        y = cy + raio * np.sin(theta + np.pi*1.5)

    elif canto == 2:  

        cx, cy = posicoes[1, 0], posicoes[1, 1]

        x = cx + raio * np.cos(theta + np.pi)

        y = cy + raio * np.sin(theta + np.pi)

    elif canto == 3:  

        cx, cy = posicoes[2, 0], posicoes[2, 1]

        x = cx + raio * np.cos(theta + np.pi/2)

        y = cy + raio * np.sin(theta + np.pi/2)

    elif canto == 4:  

        cx, cy = posicoes[3, 0], posicoes[3, 1]

        x = cx + raio * np.cos(theta)

        y = cy + raio * np.sin(theta)

    return x, y



app = dash.Dash(__name__)



app.layout = html.Div(style={'backgroundColor': 'white', 'color': 'black', 'fontFamily': 'sans-serif', 'padding': '20px','position': 'relative'}, children=[

    html.Div([

        html.Img(

            src=app.get_asset_url('logoAmanaci.png'),

            className='logo'

        )

    ]),

    html.Div(id='texto-alerta', className='alerta'),

    html.Div(id='esp-msg', className='esp_designer'),

    html.Div(id='espnow-sta', className='espnow'),

   

    html.Div(

        className='dashboard-container',

        children=[

            html.Div(

                className='painel-controle',

                children=[

                    html.Label("Visualização", className='titulo-painel'),

                    dcc.RadioItems(

                        id='tipo-visualizacao',

                        options=[

                            {'label': ' Gradual (Interpolação)', 'value': 'gradual'},

                            {'label': ' Triangular (Setores Rígidos)', 'value': 'triangular'}

                        ],

                        value='gradual',

                        labelStyle={'display': 'block', 'marginBottom': '12px', 'cursor': 'pointer'},

                        style={'color': '#333'}

                    )

                ]

            ),

            html.Div(

                className='grafico-wrapper',

                children=[

                    dcc.Graph(id='mapa-umidade', style={'height': '75vh', 'width': '65vw'})

                ]

            )

        ]

    ),

    dcc.Interval(id='intervalo-atualizacao', interval=500, n_intervals=0)

])



@app.callback(

    Output('mapa-umidade', 'figure'),

    Output('texto-alerta', 'children'),

    Output('esp-msg', 'children'),

    Output('espnow-sta', 'children'),

    Input('intervalo-atualizacao', 'n_intervals'),

    Input('tipo-visualizacao', 'value')

)

def update_graph(n, modo_visao):

    global valores_setores

    valores_setores = [0, 0, 0, 0, 0]

    u = dados_sensores["umidades"]

    b = dados_sensores["bombas"]

   

    fig = go.Figure()

    x_hover = x_range + 10

    x_value = np.tile(x_hover, (len(y_range), 1))

   

    gradiente = [

        [0.0, '#2ECC71'],  

        [0.5, "#1A96BC"],  

        [1.0, "#06456E"]    

    ]



    if modo_visao == 'gradual':

        grid = calcular_gradiente(u)

        fig.add_trace(go.Contour(

            z=grid, x=x_range, y=y_range,

            contours_coloring='heatmap',

            colorscale=gradiente,

            reversescale=False,

            line_width=0,

            ncontours=15,

            zmin=0, zmax=100,

            customdata=x_value,

            colorbar=dict(

                title=dict(text="Umidade %", side="right", font=dict(color="black", size=14)),

                ticksuffix="%",

                dtick=20,

                tickfont=dict(color="black", size=12)

            ),

            hovertemplate="Coord: %{customdata:.1f}, %{y:.1f}m<br>Estimado: %{z:.1f}%<extra></extra>"

        ))

    else:

        grid, valores_setores = calcular_triangulares(u, x_range, y_range)

        fig.add_trace(go.Contour(

            z=grid, x=x_range, y=y_range,

            contours_coloring='heatmap',

            colorscale=gradiente,

            reversescale=False,

            line_width=0,

            line_smoothing=0,

            ncontours=4,      

            zmin=0, zmax=100,

            customdata=x_value,

            colorbar=dict(

                title=dict(text="Umidade %", side="right", font=dict(color="black", size=14)),

                ticksuffix="%",

                dtick=20,

                tickfont=dict(color="black", size=12)

            ),

            hovertemplate="Coord: %{customdata:.1f}m, %{y:.1f}m<br>Estimado: %{z:.1f}%<extra></extra>"

        ))



    # Renderização estrutural das tubulações fixas e das gotículas animadas

    for i in range(1, 5):

        tx, ty = gerar_arco_tubulacao(canto=i, raio=22, num_pontos=40)

       

        # Desenha o tubo físico branco sempre visível

        fig.add_trace(go.Scatter(

            x=tx, y=ty,

            mode='lines',

            line=dict(color='white', width=4),

            hoverinfo='skip',

            showlegend=False

        ))

       

        # Só renderiza a animação da água se o sensor estiver transmitindo ativamente

        if len(b) >= i and b[i-1] == 1 and dados_sensores["conectado"] and dados_sensores["recebendoInfo"]:

            passo_animacao = (n % 4) / 4.0

            indices_agua = np.linspace(0, len(tx) - 1, 5, dtype=int)

           

            x_agua = []

            y_agua = []

            for idx in indices_agua:

                pos_atual = (idx + passo_animacao * (len(tx)/5)) % len(tx)

                int_pos = int(pos_atual)

                x_agua.append(tx[int_pos])

                y_agua.append(ty[int_pos])



            fig.add_trace(go.Scatter(

                x=x_agua, y=y_agua,

                mode='markers',

                marker=dict(size=7, color='#1A96BC', symbol='circle'),

                hoverinfo='skip',

                showlegend=False

            ))



    fig.add_trace(go.Scatter(

        x=[x_range[12], x_range[19], x_range[12], x_range[5]],

        y=[y_range[19], y_range[12], y_range[5], y_range[12]],

        mode='text',

        text=["SETOR A", "SETOR B", "SETOR C", "SETOR D"],

        textfont=dict(size=20, color="rgba(0, 0, 0, 0.5)", family="Arial Black"),

        hoverinfo='skip'

    ))



    cores_sensores = ['#FF5733', '#33FF57', '#3357FF', '#F3FF33', '#FF33F3']



    fig.add_trace(go.Scatter(

        x=posicoes[:,0], y=posicoes[:,1],

        mode='markers',

        marker=dict(size=15, color=cores_sensores, symbol='diamond', line=dict(color='black', width=2)),

        hoverinfo='skip'

    ))

   

    x_legenda = [x_range[0]-50, x_range[0]-50, x_range[0]-50, x_range[0]-50, x_range[0]-50]

    y_legenda = [y_range[16], y_range[14], y_range[12], y_range[10], y_range[8]]

   

    texto_legenda = [

        f"Sensor 1: {u[0]}%",

        f"Sensor 2: {u[1]}%",

        f"Sensor 3: {u[2]}%",

        f"Sensor 4: {u[3]}%",

        f"Sensor 5: {u[4]}%",

    ]

    fig.add_trace(go.Scatter(

        x=x_legenda,

        y=y_legenda,

        mode='markers+text',

        text=texto_legenda,

        textposition="middle right",

        marker=dict(

            size=12,

            color=cores_sensores,

            symbol='diamond',      

            line=dict(color='black', width=1)

        ),

        textfont=dict(family="Arial", size=13, color="black", weight="bold"),

        hoverinfo='skip'

    ))



    fig.add_trace(go.Scatter(

        x=[x_range[3]-60, x_range[7]-60],

        y=[y_range[24], y_range[24]],

        mode='text',

        text=["Sensores", f"Setores" if modo_visao == 'triangular' else ""],

        textposition="middle right",

        textfont=dict(family="Arial", size=12, color="black", weight="bold"),

        hoverinfo='skip'

    ))



    SensorMais_umido = dados_sensores["umidades"].index(max(dados_sensores["umidades"]))

    SensorMenos_umido = dados_sensores["umidades"].index(min(dados_sensores["umidades"]))



    SetorMais_umido = valores_setores.index(max(valores_setores))

    SetorMenos_umido = valores_setores.index(min(valores_setores))



    x_exibido = [x_range[0]-60, x_range[0]-60]

    y_exibido = [y_range[23], y_range[22]]

    setores = ["A", "B", "C", "D"]

    txt_exibido = [

        f" +Umido: S{SensorMais_umido+1}({u[SensorMais_umido]}%) {f"| Setor {setores[SetorMais_umido]}({valores_setores[SetorMais_umido]:.1f}%)" if modo_visao == 'triangular' else ""}",

        f" - Umido: S{SensorMenos_umido+1}({u[SensorMenos_umido]}%) {f"| Setor {setores[SetorMenos_umido]}({valores_setores[SetorMenos_umido]:.1f}%)" if modo_visao == 'triangular' else ""}"

    ]

    fig.add_trace(go.Scatter(

        x=x_exibido,

        y=y_exibido,

        mode='text',

        text=txt_exibido,

        textposition="middle right",

        textfont=dict(family="Arial", size=12, color="black", weight="bold"),

        hoverinfo='skip'

    ))



    # MARCA D'ÁGUA SE OS SENSORES ESTIVEREM OFFLINE

    if not dados_sensores["recebendoInfo"] and dados_sensores["conectado"]:

        fig.add_trace(go.Scatter(

            x=[x_range[12]],

            y=[y_range[12]],

            mode='text',

            text=["SISTEMA OFFLINE"],

            textfont=dict(size=42, color="rgba(255, 0, 0, 0.7)", family="Arial Black"),

            hoverinfo='skip'

        ))



    fig.update_layout(

        plot_bgcolor='white',

        paper_bgcolor='white',

        template='plotly_dark',

        margin=dict(l=30, r=120, t=10, b=70),

       

        xaxis=dict(

            range=[-65, 115],

            showgrid=False,

            zeroline=False,

            showticklabels=True,

            ticks="outside",

            dtick=150,

            title="",

        ),

        yaxis=dict(

            range=[-15, 115],

            showgrid=False,

            zeroline=False,

            showticklabels=True,

            ticks="outside",

            dtick=150,

            title="",

            scaleanchor="x",

            scaleratio=1

        ),

        annotations=[

            dict(

                x=x_range[0], y=y_range[0]-5, ax=x_range[24], ay=y_range[0]-5,

                xref="x", yref="y", axref="x", ayref="y",

                showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=2, arrowcolor="black"

            ),

            dict(

                x=x_range[24], y=y_range[0]-5, ax=x_range[0], ay=y_range[0]-5,

                xref="x", yref="y", axref="x", ayref="y",

                showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=2, arrowcolor="black"

            ),

            dict(

                x=x_range[12], y=y_range[0]-10, text="100 M",

                showarrow=False, font=dict(color="black", size=12)

            ),

            dict(

                x=x_range[0]-5, y=y_range[0], ax=x_range[0]-5, ay=y_range[24],

                xref="x", yref="y", axref="x", ayref="y",

                showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=2, arrowcolor="black"

            ),

            dict(

                x=x_range[0]-5, y=y_range[24], ax=x_range[0]-5, ay=y_range[0],

                xref="x", yref="y", axref="x", ayref="y",

                showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=2, arrowcolor="black"

            ),

            dict(

                x=x_range[0]-10, y=y_range[12], text="100 M",

                textangle=-90, showarrow=False, font=dict(color="black", size=12)

            )

        ],

        shapes=[

            dict(type="line", x0=x_range[24], y0=y_range[0], x1=x_range[0], y1=y_range[24], line=dict(color="black", width=1, dash="dot")),

            dict(type="line", x0=x_range[0], y0=y_range[0], x1=x_range[24], y1=y_range[24], line=dict(color="black", width=1, dash="dot")),

        ]

    )



    alerta_msg = ""

    esp_msg = ""

    esp_now = ""



    if dados_sensores["conectado"]:

        esp_msg = "🟢 ESP CONECTADO"

    else:

        esp_msg = "🔴 ESP DESCONECTADO"

   

    # Tratamento estrutural das mensagens de alerta no topo do gráfico

    if not dados_sensores["conectado"]:

        alerta_msg = f"❌ ERRO: ESP32 não encontrado na porta {PORTA}!"

    elif not dados_sensores["recebendoInfo"]:

        esp_now = "Conexao ESPNOW: off"

    elif dados_sensores["alerta"]:

        esp_now = "Conexao ESPNOW: on"

        alerta_msg = f"⚠️ ALERTA: Umidade Baixa nos setores: {dados_sensores['alerta']}"

    else:

        esp_now = "Conexao ESPNOW: on"



    return fig, alerta_msg, esp_msg, esp_now



if __name__ == '__main__':

    app.run(debug=False) 

