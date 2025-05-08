import dash_ag_grid as dag


def sentiment_to_color(neg, neu, pos):
    if neu > max(neg, pos):
        return 'rgba(255,255,255,1.0)'
    return f"rgba({int(neg*255)}, {int(pos*255)}, 0, 1.0)"
    
def render_message_html(message):

    url = f"https://t.me/{message['account']}/{message['id']}"

    color_sentiment = sentiment_to_color(neg=message['negative'], neu=message['neutral'], pos=message['positive'])

    # Start HTML string
    html = f"""
    <style>
        .tooltiptext:hover +.hide {{visibility: visible;}}
	    .hide {{visibility: hidden;}}

    </style>

    <div style="background-color:#2c2c2c;border-left:5px solid {color_sentiment};padding:10px;margin-bottom:8px;margin-right:8px;border-radius:4px;color:white;">
        <div style="display:flex;justify-content:space-between;align-items:center;">

            <div style="display:flex;align-items:center;position: relative;">
                <img class="tooltiptext user-icon" src="./assets/user_r.png" height="16" style="margin-right:5px;cursor:pointer;">
                <span class="hide" style="font-size: 10px; width: 140px; background-color: #c2c2c2; color: black; text-align: center; border-radius: 5px; padding: 5px; position: absolute; top: 1px; left: 30px;">Filter on user {message['account']}</span>
                <span style="float:left;vertical-align:top;">{message['account']}</span>
            </div>

            <div style="display:flex;align-items:center;margin-left:auto;">
                <a href="{url}" target="_blank">
                    <img src="./assets/link_r.png" height="16" style="margin-right:5px;">
                </a>
                <span style="float:right;">{message['date']}</span>
            </div>
        </div>
        <div style="margin-top:5px;margin-bottom:5px;">{message['text_english']}</div>
        <div style="display:flex;gap:5px;">
            <div style="display:flex;align-items:center;">
    """

    if message.get('coordinates'):
        for (lat, lon), geoloc in zip(message['coordinates'], message['geolocs']):
            html += f"""
                <img src="./assets/location_r.png" height="16" style="margin-right:5px;cursor:pointer;" title="{geoloc}" data-lat={lat} data-lon={lon} class="location-icon">
            """

    if message.get('has_photo'):
        html += '<img src="./assets/photo_r.png" height="16" style="margin-right:5px;">'
    
    if message.get('has_video'):
        html += '<img src="./assets/video_r.png" height="16">'

    html += """
            </div>
            <div style="margin-left:auto;cursor:pointer;margin-right: 0;">
                <img class="tooltiptext similar-icon" src="./assets/similar_r.png" height="16" style="margin-right:-120px;cursor:pointer;">
                <span class="hide" style="font-size: 10px; width: 140px; background-color: #c2c2c2; color: black; text-align: center; border-radius: 5px; padding: 5px; position: relative; top: 0px; right: 40px;">Search for similar messages</span>
            </div>
            
        </div>
    </div>
    """

    return html


def generate_grid(messages):

    columnDefs = [
    {'field': 'message_html', 'cellRenderer': 'RenderHTML'},
    {'field': 'account', 'hide': True},  # Invisible column
    {'field': 'sim', 'hide': True}
    ]

    grid = dag.AgGrid(
        id='messages-dag',
        columnDefs=columnDefs,
        rowData=messages,
        columnSize='responsiveSizeToFit',
        dashGridOptions={
            'headerHeight':0, 
            'rowStyle': { 'border': 'none'},
            'suppressCellFocus': True
            },
        style={'height': '100%', 'width': '100%'},
        className='no-border-grid',
        defaultColDef={
            'sortable': True, 'filter': True,
            'cellStyle': {'backgroundColor': '#3c3c3c', 'color': 'white', 'padding': '0px'},
            'wrapText': True,  # Ensure text wraps within the cell
            'autoHeight': True  # Automatically adjust the height of the row based on content
        }
    )

    return grid
