from .all_imports import *
from .select_batch_k_means import *


def register_callbacks(app):
    @app.callback(Output('ground', 'figure'),
                   [Input('start', 'n_clicks'),
                    Input('submit', 'n_clicks'),],
                  [State('select-dataset','value'),
                   State('dim', 'value')])
    def plot_ground_truth(start, submit, dataset, dim):
        print("plotting ground truth")
        time.sleep(1)
        x = np.load('.cache/x.npy')
        y = np.load('.cache/y.npy')
        principals = visualize(x, dim)
        positive = (y == 1)
        print(positive)
        negative = (y == 0)
        data = [go.Scattergl(x=principals[positive, 0],
                          y=principals[positive, 1],
                          name='1',
                          mode='markers'),
               go.Scattergl(x=principals[negative, 0],
                          y=principals[negative, 1],
                            name='0',
                          mode='markers')
               ]
        return go.Figure(data, layout=go.Layout(title='Ground truth'))

    @app.callback([Output('scatter-hidden', 'figure'),
                   Output('label', 'children'),
                   Output('store', 'data'),
                   Output('radio_label', 'options'),
                   Output('n_times', 'value'),
                   Output('start_timer', 'data')],
                  [Input('next_round', 'n_clicks'),
                   Input('start', 'n_clicks')],
                  [State('select-dataset', 'value'),
                  State('query-batch-size', 'value'),
                   State('dim', 'value'),
                   State('store', 'data')])
    def update_scatter_plot(n_clicks, start, dataset, batch_size, dim, storedata):
        print("entered update_scatter_plot")
        start_timer = 0
        df, x, y = get_dataset(dataset)
        # Original data x and y
        np.save('.cache/x.npy', x)
        np.save('.cache/y.npy', y)
        if storedata is None:
            storedata = 0
        if start is None:
            start = 0
        if n_clicks is None or n_clicks == 0 or start > storedata:
            visible = False
            n_clicks = 0
            query_indices, x_pool, y_pool = init_active_learner(x, y, batch_size)
            uncertainity = np.empty(x_pool.shape)

        else:
            visible = 'legendonly'
            x_pool = np.load('.cache/x_pool.npy')
            df = pd.read_pickle('.cache/df.pkl')
            learner = pickle.load(open(filename, 'rb'))
            query_indices, query_instance, uncertainity = learner.query(x_pool)

        # Plot the query instances
        principals = visualize(x_pool, dim)
        df_pca = pd.DataFrame(principals, columns=['1', '2'])
        selected = principals[query_indices]
        heatmap_indices = np.random.randint(low=0, high=x_pool.shape[0], size=100)
        colorscale = [[0, 'mediumturquoise'], [1, 'lightsalmon']]
        np.append(heatmap_indices, query_indices)
        if n_clicks > 0:
            name = 'Batch'+str(n_clicks)
            start_timer = time.time()
        else:
            name = 'init random train set'
        data = [
            go.Scattergl(x=df_pca['1'],
                       y=df_pca['2'],
                       mode='markers',
                       marker=dict(color='lightblue'),
                       name='unlabeled data'),
            go.Scattergl(x=selected[:, 0],
                       y=selected[:, 1],
                       mode='markers',
                       marker=dict(color='royalblue'),
                       # size=10,
                       # line=dict(color='royalblue', width=10)),
                       name=name),
            go.Contour(x=df_pca.iloc[heatmap_indices, 0],
                       y=df_pca.iloc[heatmap_indices, 1],
                       z=uncertainity[heatmap_indices],
                       name='uncertainity map',
                       visible=visible,
                       showlegend=True,
                       connectgaps=True,
                       showscale=False,
                       colorscale=colorscale,
                       line=dict(width=0),
                       contours=dict(coloring="heatmap",
                                     showlines=False
                                     )
                       ),
        ]
        layout = go.Layout(

            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            clickmode='event+select')
        #if n_clicks is None or n_clicks == 0 or start > storedata:
        fig = go.Figure(data, layout)

        # Labels
        values = np.unique(y)

        labels = df['target'].unique()
        tuple_list = zip(values, labels)
        options = []
        if n_clicks > 0:
            for l, value in tuple_list:
                options.append({'label': l, 'value': value})
        # Save files
        np.save('.cache/selected.npy', selected)
        df.ix[query_indices].to_pickle('.cache/selected.pkl')
        df.drop(query_indices, inplace=True)
        df = df.reset_index(drop=True)
        df.to_pickle('.cache/df.pkl')
        df_pca.to_pickle('.cache/df_pca.pkl')

        return fig, dataset, start, options, n_clicks, start_timer

    @app.callback(
        [Output('query_data', 'children'),
         Output('scatter','figure')],
        [Input('n_times', 'value'),
         Input('submit', 'n_clicks'),
         ],
        [State('select-dataset', 'value'),
         State('scatter-hidden', 'figure')]
        )
    def enable_query(next_round, submit, dataset, fig):
        print("entered enable_query")
        start = time.time()
        if fig is None:
            fig = go.Figure()
        image = " "
        if next_round is None or next_round == 0:
            return image, fig
        try:
            index = 0
            selected_df = pd.read_pickle('.cache/selected.pkl')
            selected = np.load('.cache/selected.npy')
        except ValueError:
            pass
        if not selected_df.empty:
            if dataset == "mnist":
                selected_df = selected_df.reset_index(drop=True)
                if 'target' in selected_df.columns:
                    selected_df.drop('target', inplace=True, axis=1)
                image_vector = selected_df.to_numpy()[index]
                image_np = image_vector.reshape(8, 8).astype(np.float64)
                #print(image_np)
                image_b64 = numpy_to_b64(image_np)
                image = html.Img(
                    src="data:image/png;base64, " + image_b64,
                    style={"display": "block", "height": "10vh", "margin": "auto"},
                )

            else:
                index = 0
                selected_df = selected_df.reset_index(drop=True)
                image = html.Div(html.H6(selected_df.ix[index]['text']))

            fig['data'].append(go.Scattergl(x=[selected[0, 0]],
                           y=[selected[0, 1]],
                           mode='markers',
                           name='current query',
                           marker=dict(symbol='star', color='rgba(0, 0, 0,1)')))
            selected = np.delete(selected, 0, axis=0)

            selected_df.drop(0, inplace=True, axis=0)
            selected_df.to_pickle('.cache/selected.pkl')
            np.save('.cache/selected.npy', selected)
        end = time.time()
        print(end-start)
        return image, fig

    @app.callback(
        [
         Output('hidden-div', 'children'),
         Output('store_dataset', 'data')],
        [Input('scatter', 'selectedData'),
         Input('submit', 'n_clicks'),
         Input('start', 'n_clicks'),
         ],
        [State('store_dataset', 'data'),
         State('hidden-div', 'children'),
         State('radio_label', 'value')])
    def get_selected_data(clickData, submit,  start, store, previous, radio_label):
        if store is None:
            store = 0
        if start is None:
            start = 0

        if previous is None or start > store:
            result_dict = dict()
            result_dict['clicks'] = 0
            #result_dict['points'] = []
            result_dict['queries'] = []
        else:
            if radio_label is not None and previous is not None:
                if submit > literal_eval(previous)["clicks"]:

                    previous_list = json.loads(previous)
                    result_dict = previous_list
                    #points = previous_list['points'] + clickData['points']
                    queries = previous_list['queries']+[int(radio_label)]
                    #result_dict['points'] = points
                    result_dict['clicks'] = submit
                    result_dict['queries'] = queries
                else:
                    result_dict = json.loads(previous)
            else:
                result_dict = json.loads(previous)

        return json.dumps(result_dict), start

    @app.callback(
        [Output('decision', 'figure'),
         Output('score', 'children'),
         ],
        [Input('hidden-div', 'children'),
         Input('next_round', 'n_clicks'),
         Input('query-batch-size', 'value'),
         Input('label', 'children'),
         Input('select-dataset', 'value'),

         ], [State('querystore', 'data'),
             State('start_timer', 'data')])
    def perform_active_learning(previous, n_clicks, batch_size, labels, dataset, query_round,
                                start_timer):
        decision = go.Figure()
        score = ''
        show_fig = 0


        if n_clicks is None and labels == dataset:
            start_timer = 0
            end = time.time()
            show_fig = 1
            x = np.load('.cache/x.npy')
            y = np.load('.cache/y.npy')
            learner = pickle.load(open(filename, 'rb'))

        else:
            if previous and n_clicks is not None:

                if(literal_eval(previous)["clicks"]) == (batch_size*n_clicks):
                    show_fig=1

                    end = time.time()
                    x = np.load('.cache/x.npy')
                    y = np.load('.cache/y.npy')

                    x_pool = np.load('.cache/x_pool.npy')
                    y_pool = np.load('.cache/y_pool.npy')

                    learner = pickle.load(open(filename, 'rb'))
                    query_results = literal_eval(previous)['queries'][0:batch_size]
                    query_indices = list(range(0, batch_size))
                    learner.teach(x[query_indices], query_results)
                    # Active learner supports numpy matrices, hence use .values


                    x_pool = np.delete(x_pool, query_indices, axis=0)
                    y_pool = np.delete(y_pool, query_indices)
                    np.save('.cache/x_pool.npy', x_pool)
                    np.save('.cache/y_pool.npy', y_pool)
        if show_fig == 1:
            df_pca = pd.read_pickle('.cache/df_pca.pkl')
            predictions = learner.predict(x)
            is_correct = (predictions == y)
            df = pd.DataFrame(x)
            df['y'] = predictions
            principals = visualize(df.as_matrix(), dim='pca')
            df_pca_output = pd.DataFrame(principals, columns=['1', '2'])


            f1_score = sklearn.metrics.f1_score(y, predictions)
            confusion_matrix = sklearn.metrics.confusion_matrix(y, predictions)
            print(confusion_matrix)
            cm_data = [go.Heatmap(x=np.unique(y),
                                  y=np.unique(y),
                                  z=confusion_matrix)]
            cm_fig = dcc.Graph(figure=go.Figure(data=cm_data,
                                                layout=go.Layout(
                                                    xaxis={'title': 'Predicted labels',
                                                           'side': 'bottom'},
                                                    yaxis={'title': 'True labels',
                                                           "autorange": "reversed"},
                                                    height=400, width=400)
                                                ),
                               )
            score = html.Div([html.H5('Batch # ' + str(n_clicks)),
                              html.P('F1 Score: ' + str(round(f1_score, 3))),
                              html.P(' Time for batch: ' +
                                     str(round(end - start_timer)) + ' sec'),
                              html.P('Confusion Matrix: '),
                              cm_fig
                              ])
            data_dec = [

                go.Scattergl(x=df_pca['1'].values[predictions == 1],
                             y=df_pca['2'].values[predictions == 1],
                             mode='markers',
                             name='1',
                             marker=dict(size=12,
                                         color='blue')),

                go.Scattergl(x=df_pca['1'].values[predictions == 0],
                             y=df_pca['2'].values[predictions == 0],
                             mode='markers',
                             name='0',
                             marker=dict(size=12,
                                         color='red',
                                         )),

                go.Scattergl(x=df_pca['1'].values[~is_correct],
                             y=df_pca['2'].values[~is_correct],
                             mode='markers',
                             name='wrong predictions',
                             marker=dict(symbol="x",
                                         opacity=0.7,
                                         size=8,
                                         color='black'
                                         )),
            ]
            decision = go.Figure(data_dec, layout=go.Layout(title='Output of classfier'))

        return decision, score



def get_dataset(dataset):
    if dataset == "mnist":
        raw_data = load_digits()  # fetch_openml('mnist_784', version=1)
        df = pd.DataFrame(data=raw_data['data'])
        df['target'] = raw_data['target']
        x = raw_data['data']
        y = raw_data['target'].astype(np.uint8)

    else:
        df = pd.read_pickle('datasets/'+dataset+".pkl")
        df.dropna(axis=0, inplace=True)
        x = df['text'].values
        y = df['label'].values
        nltk.download('stopwords')
        tfid = TfidfVectorizer(max_features=1500, min_df=5, max_df=0.7,
                               stop_words=stopwords.words('english'))
        x = tfid.fit_transform(x).toarray()
        df['target'] = df['label']
        print(df['target'].value_counts())
        df.drop('text', axis=1)

    # else: Support only image and text for now
    #     if dataset == 'bc':
    #         raw_data = load_breast_cancer()
    #     elif dataset == 'iris':
    #         raw_data = load_iris()
    #     elif dataset == "wine":
    #         raw_data = load_wine()
    #     df = pd.DataFrame(data=np.c_[raw_data['data'], raw_data['target']],
    #                       columns=list(raw_data['feature_names']) + ['target'])
    #     x = raw_data['data']
    #     y = raw_data['target'].astype(np.uint8)
    #print(df.head())
    return df, x, y


def numpy_to_b64(array, scalar=True):
    # Convert from 0-1 to 0-255
    if scalar:
        array = np.uint8(255 * array)

    im_pil = Image.fromarray(array)
    buff = BytesIO()
    im_pil.save(buff, format="png")
    im_b64 = base64.b64encode(buff.getvalue()).decode("utf-8")
    return im_b64


def visualize(x_pool, dim):
    print(x_pool.shape)
    if dim == "pca":
        pca = PCA(n_components=2, random_state=100)
        principals = pca.fit_transform(x_pool)
    elif dim == "tsne":
        tsne = TSNE(n_components=2, random_state=100, n_jobs=4, metric='cosine')
        principals = tsne.fit_transform(x_pool)
    else:
        umaps = umap.UMAP(n_components=2, random_state=100)
        principals= umaps.fit_transform(x_pool)
    return principals


def init_active_learner(x, y, batch_size):

    query_indices = np.random.randint(low=0, high=x.shape[0], size=round(0.1*x.shape[0]))

    x_train = x[query_indices]
    y_train = y[query_indices]

    # ML model
    # rf = RandomForestClassifier(n_jobs=-1, n_estimators=20,
    #                             max_features=0.7,
    #                             oob_score=True
    #                            # class_weight={0: 1, 1: 2}
    #                             )
    #rf = KNeighborsClassifier(n_neighbors=5, n_jobs=4)
    svm = LinearSVC()
    estimator = CalibratedClassifierCV(svm)

    #SVC(kernel='linear', probability=True, gamma='auto')


    # batch sampling
    preset_batch = partial(batch_kmeans, n_instances=batch_size, selection_strategy='k-means-closest')
    # AL model
    learner = ActiveLearner(estimator=estimator,
                            X_training=x_train,
                            y_training=y_train.ravel(),
                            query_strategy=preset_batch)
    pickle.dump(learner, open(filename, 'wb'))
    x_pool = np.delete(x, query_indices, axis=0)
    y_pool = np.delete(y, query_indices, axis=0)

    np.save('.cache/x_pool.npy', x_pool)
    np.save('.cache/y_pool.npy', y_pool)
    return query_indices, x, y