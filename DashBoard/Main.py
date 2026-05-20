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

dados_sensores = {"umidades": [0, 0, 0, 0, 0], "recebendoInfo": False, "alerta": "", "conectado": False}

def leitor_serial():
    global dados_sensores
    
    while True: 
        try:
            print(f"Procurando ESP32 na porta {PORTA}...")
            ser = serial.Serial(PORTA, BAUD, timeout=1)
            ser.flush()
            print(f"Conectado com sucesso na porta {PORTA}!")
            dados_sensores["conectado"] = True
            
            while True:
                if ser.in_waiting > 0:
                    try:
                        line = ser.readline().decode('utf-8', errors='ignore').strip()
                        
                        if "Recebido via ESP-NOW" in line:
                            dados_sensores["recebendoInfo"] = True
                            texto_numeros = line.split(':')[-1].strip()
                            partes = texto_numeros.split(',')
                            
                            temp_umid = []
                            alertas = []
                            
                            for idx, item in enumerate(partes):
                                try:
                                    valor = int(item.strip())
                                    temp_umid.append(valor)
                                    
                                    if valor < 30:
                                        nome_sensor = f"Sensor {idx + 1}"
                                        alertas.append(nome_sensor)
                                except ValueError:
                                    continue
                                    
                            if len(temp_umid) == 5:
                                dados_sensores["umidades"] = temp_umid
                                dados_sensores["alerta"] = ", ".join(alertas)
                        
                        elif "Umidade" in line:
                            dados_sensores["recebendoInfo"] = True
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
                        
                        if "Conexao perdida com o ESP" in line:
                            dados_sensores["recebendoInfo"] = False
                            print("ConexaoPerdida")
                        elif "[CONEXÃO REESTABELECIDA]" in line:
                            dados_sensores["recebendoInfo"] = True
                            print("ConexaoVolta")
                                
                    except (ValueError, IndexError):
                        continue 
                        
        except Exception as e:
            dados_sensores["conectado"] = False
            print(f"Dispositivo não encontrado ou desconectado. Tentando novamente em 2 segundos...")
            time.sleep(2)

threading.Thread(target=leitor_serial, daemon=True).start()

x_range = np.linspace(-10, 90, 25)
y_range = np.linspace(0, 100, 25)
posicoes = np.array([
    [x_range[0],  y_range[24]], # Canto Superior Esquerdo: [-10, 100]
    [x_range[24], y_range[24]], # Canto Superior Direito:  [90, 100]
    [x_range[24], y_range[0]],  # Canto Inferior Direito:  [90, 0]
    [x_range[0],  y_range[0]],  # Canto Inferior Esquerdo: [-10, 0]
    [x_range[12], y_range[12]]  # Ponto Central:             [40, 50]
])
X, Y = np.meshgrid(x_range, y_range)

def calcular_triangulares(u, x_range, y_range):
    """
    Calcula a média de cada setor triangular e monta uma matriz rígida 
    que respeita as diagonais do quadrado.
    """
    setor_A = (u[0] + u[1] + u[4]) / 3  # Triângulo Superior
    setor_B = (u[1] + u[2] + u[4]) / 3  # Triângulo Direito
    setor_C = (u[2] + u[3] + u[4]) / 3  # Triângulo Inferior
    setor_D = (u[3] + u[0] + u[4]) / 3  # Triângulo Esquerdo

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
    
    # Distância limite (em metros).
    D_MAX = 70.0 
    
    for i in range(len(posicoes)):
        # Calcula a distância real do ponto até o sensor
        dist = np.sqrt((X - posicoes[i,0])**2 + (Y - posicoes[i,1])**2)
        dist = np.maximum(dist, 1.0)
        
        termo_suave = (np.maximum(0.0, D_MAX - dist) / (D_MAX * dist)) ** 2
        
        peso = termo_suave
        
        acum_v += peso * valores[i]
        acum_p += peso
        
    return np.where(acum_p > 0, acum_v / acum_p, 0.0)

app = dash.Dash(__name__)

app.layout = html.Div(style={'backgroundColor': 'white', 'color': 'black', 'fontFamily': 'sans-serif', 'padding': '20px','position': 'relative'}, children=[
    
    # Container da Logo
    html.Div([
        html.Img(
            src=app.get_asset_url('logoAmanaci.png'),
            className='logo'
        )
    ]),
    # Texto de Alerta
    html.Div(
        id='texto-alerta', 
        className='alerta'
    ),
    # Texto aviso esp conectado/desconectado
    html.Div(
        id='esp-msg',
        className='esp_designer'
    ),
    html.Div(
        id='espnow-sta',
        className='espnow'
    ),
    # Coloca os botões e o gráfico lado a lado
    html.Div(
        className='dashboard-container',
        children=[
            
            # Painel de Controle (Botões)
            html.Div(
                className='painel-controle',
                children=[
                    html.Label(
                        "Visualização", 
                        className='titulo-painel'
                    ),
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
            
            # O Gráfico do Hectare
            html.Div(
                className='grafico-wrapper', 
                children=[
                    dcc.Graph(id='mapa-umidade', style={'height': '75vh', 'width': '65vw'})
                ]
            )
            
        ]
    ),


    # Componente invisível de tempo
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
    
    fig = go.Figure()
    
    x_hover = x_range + 10
    x_value = np.tile(x_hover, (len(y_range), 1))
    
    gradiente = [# gradiente utilizado para exibir valores
        [0.0, '#2ECC71'],   
        [0.5, "#1A96BC"],   
        [1.0, "#06456E"]    
    ]

    if modo_visao == 'gradual':# visao gradual, exibe valores em gradiente
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
        
    else:# valor triangular, exibe valores utilizando a media entre os sensores que estao no setor
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

    # SETORES (A, B, C, D)
    fig.add_trace(go.Scatter(
        x=[x_range[12], x_range[19], x_range[12], x_range[5]], 
        y=[y_range[19], y_range[12], y_range[5], y_range[12]],
        mode='text',
        text=["SETOR A", "SETOR B", "SETOR C", "SETOR D"],
        textfont=dict(size=20, color="rgba(0, 0, 0, 0.5)", family="Arial Black"),
        hoverinfo='skip'
    ))

    cores_sensores = ['#FF5733', '#33FF57', '#3357FF', '#F3FF33', '#FF33F3'] 

    # SENSORES
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


    # valores de comparacoes
    fig.add_trace(go.Scatter(
        x=[x_range[3]-60,x_range[7]-60],
        y=[y_range[24],y_range[24]],
        mode='text',
        text=["Sensores",f"Setores" if modo_visao == 'triangular' else ""],
        textposition="middle right", 
        textfont=dict(family="Arial", size=12, color="black", weight="bold"),
        hoverinfo='skip'
    ))

    SensorMais_umido = dados_sensores["umidades"].index(max(dados_sensores["umidades"]))
    SensorMenos_umido = dados_sensores["umidades"].index(min(dados_sensores["umidades"]))

    SetorMais_umido = valores_setores.index(max(valores_setores))
    SetorMenos_umido = valores_setores.index(min(valores_setores))


    x_exibido = [x_range[0]-60,x_range[0]-60] 
    y_exibido = [y_range[23], y_range[22]]
    setores = ["A","B","C","D"]
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
    # valores comparacao

    # grafico
    fig.update_layout(
        plot_bgcolor='white',
        paper_bgcolor='white', 
        template='plotly_dark',
        margin=dict(l=30, r=120, t=10, b=70),# left, right, top, bottom
        
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
            # COTA EIXO X (LARGURA)
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

            # COTA EIXO Y (ALTURA)
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
        dados_sensores["umidades"] = [0,0,0,0,0]
    

    if not dados_sensores["conectado"]:
        alerta_msg = f"❌ ERRO: ESP32 não encontrado na porta {PORTA}!"
    elif dados_sensores["alerta"]:
        alerta_msg = f"⚠️ ALERTA: Umidade Baixa nos sensores: {dados_sensores['alerta']}"
    elif not dados_sensores["recebendoInfo"]:
        esp_now = "Conexao ESPNOW: off"
        dados_sensores["umidades"] = [0,0,0,0,0]
        alerta_msg = "Sensores Offline!"

    return fig, alerta_msg,esp_msg,esp_now

if __name__ == '__main__':
    app.run(debug=False)