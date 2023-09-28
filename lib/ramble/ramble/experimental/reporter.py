# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import llnl.util.tty as tty
import ramble.experimental.uploader



class Reporter():
    def __init__(self, workspace):
        self.workspace = workspace
    def report():
        print("Null report.")


class BokehReporter(Reporter):
    def __init__(self, workspace):
        super()

    def report(self):
        try:
            from bokeh.plotting import figure, output_file, show
            from bokeh.layouts import row, column, gridplot
        except ImportError or ModuleNotFoundError:
            tty.die('Dash python module not found. Ensure requirements.txt are installed.')
        # TODO: wire up to actual FOM data

        p1 = figure()
        p1.circle([1, 2, 3], [4, 5, 6], color="orange")


        fruits = ['Apples', 'Pears', 'Nectarines', 'Plums', 'Grapes', 'Strawberries']
        counts = [5, 3, 4, 2, 4, 6]

        p = figure(x_range=fruits, height=350, title="Fruit Counts",
                   toolbar_location=None, tools="")

        p.vbar(x=fruits, top=counts, width=0.9)

        p.xgrid.grid_line_color = None
        p.y_range.start = 0
        p2 = p

        p3 = p1

        plot = column([p1, p2, p3], sizing_mode='stretch_both')

        output_file("foo.html")

        show(plot)

class MatplotlibReporter(Reporter):
    def __init__(self, workspace):
        super()

    def report(self):
        # TODO: implement
        # Also try seaborn?
        pass

class PlotlyReporter(Reporter):
    def __init__(self, workspace):
        super().__init__(workspace)

    def generate_plot(self):
        self.report()

        # imports
        import plotly
        import plotly.express as px

        # data
        formatted_data = ramble.experimental.uploader.format_data(self.workspace.results)

        exps_to_insert = []
        foms_to_insert = []
        for experiment in formatted_data:
            experiment.generate_hash()
            exps_to_insert.append(experiment.to_json())

            for fom in experiment.foms:
                fom_data = fom
                fom_data['experiment_name'] = experiment.name
                print(fom)
                #foms_to_insert.append(fom_data)

        tmp_fom = {'name': 'Total Runtime 2', 'value': 10000, 'unit': 's', 'context': 'test', 'experiment_name': 'fake'}
        foms_to_insert.append(tmp_fom)

        # plotly express bar chart
        #fig = px.line(df, x="year", y="lifeExp", color='country')
        fig = px.bar(foms_to_insert, x='experiment_name', y='value')

        # html file
        plotly.offline.plot(fig, filename='./lifeExp.html')

    def report(self):
        try:
            from dash import Dash, dcc, html
            import plotly.express as px
            from base64 import b64encode
            import io
        except ImportError or ModuleNotFoundError:
            tty.die('Dash python module not found. Ensure requirements.txt are installed.')

        formatted_data = ramble.experimental.uploader.format_data(self.workspace.results)
        print(formatted_data)

        exps_to_insert = []
        foms_to_insert = []
        for experiment in formatted_data:
            experiment.generate_hash()
            exps_to_insert.append(experiment.to_json())

            for fom in experiment.foms:
                fom_data = fom
                fom_data['experiment_name'] = experiment.name
                print(fom)
                foms_to_insert.append(fom_data)

        tmp_fom = {'name': 'Total Runtime 2', 'value': 10000, 'unit': 's', 'context': 'test', 'experiment_name': 'fake'}
        foms_to_insert.append(tmp_fom)

        app = Dash(__name__)
        buffer = io.StringIO()

        fig = px.bar(foms_to_insert, x='experiment_name', y='value')
        #fig.show()
        fig.write_html(buffer)

        #import plotly.graph_objects as go
#animals=['giraffes', 'orangutans', 'monkeys']
#
#fig = go.Figure(data=[
    #go.Bar(name='SF Zoo', x=animals, y=[20, 14, 23]),
    #go.Bar(name='LA Zoo', x=animals, y=[12, 18, 29])
    #])
## Change the bar mode
#fig.update_layout(barmode='group')
#fig.show()

        html_bytes = buffer.getvalue().encode()
        encoded = b64encode(html_bytes).decode()

        app.layout = html.Div([
            html.H4('Simple plot export options'),
            html.P("↓↓↓ try downloading the plot as PNG ↓↓↓", style={"text-align": "right", "font-weight": "bold"}),
            dcc.Graph(id="graph", figure=fig),
            html.A(
                html.Button("Download as HTML"),
                id="download",
                href="data:text/html;base64," + encoded,
                download="plotly_graph.html"
            )
        ])

        # FIXME: Launch this on a thread and grab the output?
        #app.run_server(debug=True, use_reloader=False)
