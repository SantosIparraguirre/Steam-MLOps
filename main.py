from fastapi import FastAPI, Query
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

app = FastAPI()

@app.get("/developer", tags=["Desarrollador"])

async def developer(developer : str = Query(default='Valve', description='Ingrese el nombre de un desarrollador. Ejemplo: Kotoshiro. Salida: Cantidad de items y porcentaje de contenido free por año')):
    
    # Cargamos el dataset.
    df = pd.read_parquet('./Datasets/developer_endpoint.parquet')

    # Filtramos por el desarrollador ingresado.
    df = df[df['developer'] == developer.strip().title()]

    # Si el desarrollador ingresado no coincide, devolvemos un mensaje de error.

    if df.empty:
        return {'Desarrollador no encontrado.'}

    # Creamos la columna año en base a la columna release_date.
    df['Año'] = df['release_date'].dt.year

    # Agrupamos por año y contamos la cantidad de items.
    df_year = df.groupby('Año').size().reset_index(name='Cantidad de Items')

    # Agrupamos por año y sumamos la cantidad de items free.
    df_free = df.groupby('Año')['free'].sum().reset_index(name='free')

    # Hacemos un merge de ambos dataframes mediante la columna Año.
    df = pd.merge(df_year, df_free, on='Año')

    # Calculamos el porcentaje de contenido free.
    df['Contenido Free'] = round(df['free'] / df['Cantidad de Items'] * 100, 2)

    # Convertimos el porcentaje a string y le agregamos el símbolo %.
    df['Contenido Free'] = df['Contenido Free'].apply(lambda x: f'{x}%')

    # Eliminamos la columna free.
    df.drop(columns=['free'], inplace=True)

    # Convertimos el dataframe a un diccionario.
    df = df.to_dict('records')

    # Devolvemos el resultado.
    return df

@app.get("/user_data", tags=["Datos del usuario"])

async def user_data(user_id : str = Query(default='mayshowganmore', description='Ingrese el ID de un usuario. Ejemplo: 76561197970982479. Salida: Dinero gastado, porcentaje de recomendación y cantidad de items')):
    
    # Cargamos los datasets.
    df_user_reviews = pd.read_parquet('./Datasets/user_reviews_preprocessed.parquet')
    df_games = pd.read_parquet('./Datasets/steam_games_preprocessed.parquet')
    df_user_items = pd.read_parquet('./Datasets/users_items_preprocessed.parquet')

    # Convertimos user_id a string y user_id de df_user_items a string.
    user_id = str(user_id)
    df_user_items['user_id'] = df_user_items['user_id'].astype(str)

    # Filtramos df_user_items por user_id.
    df_user_items = df_user_items[df_user_items['user_id'] == user_id]

    # Si el user_id ingresado no coincide, devolvemos un mensaje de error.
    if df_user_items.empty:
        return {'Usuario no encontrado.'}

    # Obtenemos los títulos de los juegos del usuario y sus precios.
    user_game_titles = df_user_items['item_name'].tolist()
    user_game_prices = df_games[df_games['title'].isin(user_game_titles)]['price'].tolist()

    # Calculamos el dinero total gastado por el usuario.
    total_money_spent = round(sum(user_game_prices), 2)

    # Filtramos df_user_reviews por user_id.
    user_reviews = df_user_reviews[df_user_reviews['user_id'] == user_id]

    # Si no está vacío, calculamos el porcentaje de recomendación.
    if not user_reviews.empty:
        recommend_count = user_reviews['recommend'].value_counts(normalize=True)
        recommend_percentage = round(recommend_count.get(True, 0) * 100, 2)

    # Si está vacío, asignamos 0 al porcentaje de recomendación.
    else:
        recommend_percentage = 0

    # Obtenemos la cantidad de items del usuario.
    items_count = df_user_items[df_user_items['user_id'] == user_id].shape[0]

    result = {
        'Usuario': user_id,
        'Dinero gastado': f'{total_money_spent} USD',
        '% de recomendación': f'{recommend_percentage}%',
        'Cantidad de items': items_count
    }

    # Devolvemos el resultado.
    return result

@app.get("/user_for_genre", tags=["Usuario con más horas jugadas para un género"])

async def user_for_genre(genre: str = Query(default='Action', description='Ingrese un género. Ejemplo: RPG. Salida: Usuario con más horas jugadas para el género ingresado y cantidad de horas jugadas por año')):
    
    # Cargamos el dataset.
    df = pd.read_parquet('./Datasets/userforgenre_endpoint.parquet')
    
    # Filtramos por el género ingresado.
    df = df[df['genres'].str.contains(genre.strip().title(), case=False, na=False)]

    # Si el género ingresado no coincide, devolvemos un mensaje de error.
    if df.empty:
        return {'Género no encontrado'}
    
    # Guardamos en la variable user_hours la suma de las horas jugadas por usuario.
    user_hours = df.groupby('user_id')['playtime_forever'].sum().reset_index()
    
    # Obtenemos el usuario con más horas jugadas y guardamos su ID en la variable top_user_id.
    top_user = user_hours.loc[user_hours['playtime_forever'].idxmax()]
    top_user_id = top_user['user_id']
    
    # Guardamos en la variable top_user_df las filas del dataframe que corresponden al usuario con más horas jugadas.
    top_user_df = df[df['user_id'] == top_user_id]
    
    # Creamos la columna year en base a la columna release_date.
    top_user_df['year'] = top_user_df['release_date'].dt.year

    # Agrupamos por año y sumamos las horas jugadas.
    hours_by_year = top_user_df.groupby('year')['playtime_forever'].sum().reset_index()
    
    # Renombramos 'year' por 'Año' y 'playtime_forever' por 'Horas jugadas'.
    hours_by_year.rename(columns={'year': 'Año', 'playtime_forever': 'Horas jugadas'}, inplace=True)

    # Convertimos hours_by_year en diccionario.
    hours_by_year_dict = hours_by_year.to_dict(orient='records')
    
    result = {
        f"Usuario con más horas jugadas para el género {genre.strip().title()}": top_user_id,
        "Horas jugadas por año": hours_by_year_dict
    }

    # Devolvemos el resultado.
    return result

@app.get("/best_developer_year", tags=["Top 3 desarrolladores por año"])

async def best_developer_year(year: int = Query(default=2000, description='Ingrese un año. Ejemplo: 2005. Salida: Top 3 desarrolladores con más juegos recomendados y reseñas positivas para el año ingresado.')):
    
    # Cargamos el dataset.
    df = pd.read_parquet('./Datasets/best_developer_year_endpoint.parquet')

    # Creamos la columna year en base a release_date.
    df['year'] = df['release_date'].dt.year

    # Filtramos por el año ingresado.
    df = df[df['year'] == year]

    # Si el año ingresado no coincide, devolvemos un mensaje de error.
    if df.empty:
        return {'Año no encontrado.'}

    # Filtramos por recomendaciones y reseñas positivas.
    df = df[(df['recommend'] == True) & (df['sentiment_analysis'] == 2)]

    # Agrupamos por desarrollador y contamos la cantidad de recomendaciones.
    df = df.groupby('developer').size().reset_index(name='recommend_count')

    # Ordenamos de mayor a menor y obtenemos los 3 primeros.
    df = df.sort_values(by='recommend_count', ascending=False).head(3)

    # Formateamos el resultado como lista de diccionarios.
    df = [{"Puesto {}".format(i+1): row[1]} for i, row in enumerate(df.itertuples())]

    # Devolvemos el resultado.
    return df

@app.get("/developer_reviews_analysis", tags=["Reseñas por desarrollador"])

async def developer_reviews_analysis(developer : str = Query(default='Valve', description='Ingrese el nombre de un desarrollador. Ejemplo: Kotoshiro. Salida: Cantidad de reseñas positivas y negativas para el desarrollador ingresado.')):
    
    # Cargamos el dataset.
    df = pd.read_parquet('./Datasets/developer_reviews_analysis.parquet')

    # Filtramos por el desarrollador.
    df = df[df['developer'] == developer.strip().title()]

    # Creamos la variable de reviews positivas.
    positive = int((df['sentiment_analysis'] == 2).sum())

    # Creamos la variable de reviews negativas.
    negative = int((df['sentiment_analysis'] == 0).sum())

    # Creamos el diccionario de resultados.
    result = {
        developer.strip().title(): {
            'Positive': positive,
            'Negative': negative
        }
    }
    # Devolvemos el resultado.
    return result

@app.get("/recomendacion_juego", tags=["Recomendación de videojuegos"])

async def recomendacion_juego(item_id : str = Query(default='10', description='Debe ingresar un ID de juego. Ejemplo: 10 = Counter-Strike. Salida: Recomendación de 5 juegos similares.')):
    
    # Cargamos el dataset.
    df = pd.read_parquet('./Datasets/game_recommendation.parquet')

    # Verificamos si el item_id ingresado se encuentra en el dataset.
    if item_id not in df['item_id'].values:

    # Si no se encuentra, devolvemos un mensaje de error.
        return {'ID no encontrado'}
    
    # Creamos una instancia de TfidfVectorizer con las stopwords en inglés.
    tfidf = TfidfVectorizer(stop_words='english')

    # Creamos la matriz tf-idf con los features de los videojuegos.
    tfidf_matrix = tfidf.fit_transform(df['features'])

    # Obtenemos el índice del item_id ingresado.
    idx = df[df['item_id'] == item_id].index[0]

    # Obtenemos el vector tf-idf del item_id ingresado.
    item_tfidf_vector = tfidf_matrix[idx]

    # Calculamos la matriz de similitud de coseno entre el juego ingresado y los demás.
    cosine_sim_matrix = cosine_similarity(item_tfidf_vector, tfidf_matrix)

    # Guardamos los scores de similitud en una lista de tuplas, donde el primer elemento es el índice y el segundo es el score. Utilizamos un condicional para no incluir el juego ingresado.
    sim_scores = [(i, score) for i, score in enumerate(cosine_sim_matrix[0]) if i != idx]  

    # Ordenamos los scores de mayor a menor.
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)

    # Obtenemos los 5 items más similares.
    sim_scores = sim_scores[:5]

    # Obtenemos los títulos de los items recomendados y los convertimos en lista.
    recommended_games = df['title'].iloc[[i[0] for i in sim_scores]].tolist()

    result = {"Juegos recomendados": recommended_games}

    # Devolvemos los juegos recomendados.
    return result



@app.get("/recomendacion_usuario", tags=["Recomendación por usuario"])
# Este modelo no es preciso y aún está en desarrollo. Se recomienda utilizar el modelo de recomendación de videojuegos.
async def recomendacion_usuario(user_id : str = Query(default='mayshowganmore', description='Ingrese un ID de usuario. Ejemplo: 76561197970982479. Salida: Recomendación de 5 juegos para el usuario ingresado.')):
    
    # Cargamos el dataset
    df = pd.read_parquet('./Datasets/user_recommendations.parquet')

    # Convertimos user_id a string y la columna user_id del df a string.
    user_id = str(user_id)
    df['user_id'] = df['user_id'].astype(str)

    # Filtramos los juegos del usuario.
    user_games = df[df['user_id'] == user_id]

    # Si el usuario no se encuentra, devolvemos un mensaje de error.
    if user_games.empty:
        return {'Usuario no encontrado.'}

    # Calculamos la similitud de coseno entre los juegos del usuario y el resto de juegos
    tfidf = TfidfVectorizer(stop_words='english')
    tfidf_matrix = tfidf.fit_transform(df['features'])
    user_tfidf = tfidf.transform(user_games['features'])
    cosine_sim = cosine_similarity(user_tfidf, tfidf_matrix)

    # Obtenemos las puntuaciones de similitud para los juegos del usuario
    sim_scores = list(enumerate(cosine_sim[0]))

    # Ordenamos los juegos por similitud
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)

    # Filtramos los juegos que el usuario ya posee y obtenemos unicamente los títulos de los juegos recomendados
    user_owned_games = user_games['title'].tolist()
    recommended_games = [df.iloc[i]['title'] for i, sim in sim_scores if df.iloc[i]['title'] not in user_owned_games]

    # Tomamos solo los primeros 5 juegos recomendados
    recommended_games = recommended_games[:5]

    # Devolvemos los juegos recomendados
    return recommended_games