if (!window.dash_clientside) {
    window.dash_clientside = {};
}

window.dash_clientside.clientside = {
    update_graph_dimensions: function(containerStyle, containerId) {
        const container = document.getElementById(containerId);
        const containerHeight = container ? container.clientHeight : 0;
        return {
            width: '100%',
            height: containerHeight + 'px'
        }
    }
};