var dagcomponentfuncs = (window.dashAgGridComponentFunctions = window.dashAgGridComponentFunctions || {});

// adapted from: https://community.plotly.com/t/use-dropdown-link-menu-in-dash-ag-grid/84648
// related Dash documentation: https://dash.plotly.com/dash-ag-grid/cell-renderer-components#custom-cell-renderers

function iconText(icon, text, children) {
    return React.createElement(
        'div',
        null,
        React.createElement(
            'i',
            {class: 'ms-2 ' + icon},
        ),
        text,
        children
    );
}

dagcomponentfuncs.DropdownLinks = function (props) {
    const [isOpen, setIsOpen] = React.useState(false);

    const toggleDropdown = () => {
        setIsOpen(!isOpen);
    };

    const dropdownMenu = React.createElement(
        'div',
        {className: `dropdown-menu show ms-2`},
        props.value.map(([icon, title, url]) =>
            React.createElement(
                'a',
                {href: url, style: {"textDecoration": "none"}},
                iconText(icon, title)
            )
        )
    );

    return React.createElement(
        'div',
        {className: `dropdown ${isOpen ? 'show' : ''}`},
        React.createElement(
            'button',
            {
                className: 'btn btn-primary btn-sm',
                onClick: toggleDropdown
            },
            iconText('bi-link-45deg me-2', 'Links ', React.createElement(
                'i',
                {className: 'me-1 bi bi-caret-down-fill'}
            ))
        ),
        isOpen ? dropdownMenu : null
    );
}

dagcomponentfuncs.Badge = function(props) {
    let badgeColor;

    if (props.value.toLowerCase() === 'success') {
        badgeColor = 'success';
    } else if (props.value.toLowerCase() === 'failure') {
        badgeColor = 'danger';
    } else {
        badgeColor = 'warning';
    }

    return React.createElement(
        window.dash_bootstrap_components.Badge,
        {
            color: badgeColor,
            children: props.value
        }
    );
};

dagcomponentfuncs.TaskIcon = function(params) {
    var [iconName, iconColor, iconSize] = params.value.split(',');
    return React.createElement('i', {
        className: `bi bi-${iconName}`,
        style: {
            color: iconColor,
            fontSize: iconSize || '1rem'
        }
    });
}
