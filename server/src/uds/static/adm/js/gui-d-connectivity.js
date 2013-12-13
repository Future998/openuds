/* jshint strict: true */
gui.connectivity = {
    transports : new GuiElement(api.transports, 'trans'),
    networks : new GuiElement(api.networks, 'nets'),
};

gui.connectivity.link = function(event) {
    "use strict";
    api.templates.get('connectivity', function(tmpl) {
        gui.clearWorkspace();
        gui.appendToWorkspace(api.templates.evaluate(tmpl, {
            transports : 'transports-placeholder',
            networks : 'networks-placeholder'
        }));

        gui.connectivity.transports.table({
            rowSelect : 'single',
            container : 'transports-placeholder',
            buttons : [ 'new', 'edit', 'delete', 'xls' ],
            onNew : gui.methods.typedNew(gui.connectivity.transports, gettext('New transport'), gettext('Error creating transport')),
            onEdit: gui.methods.typedEdit(gui.connectivity.transports, gettext('Edit transport'), gettext('Error processing transport')),
            onDelete: gui.methods.del(gui.connectivity.transports, gettext('Delete transport'), gettext('Error deleting transport')),
        });
        gui.connectivity.networks.table({
            rowSelect : 'single',
            container : 'networks-placeholder',
            buttons : [ 'new', 'edit', 'delete', 'xls' ],
            onNew : gui.methods.typedNew(gui.connectivity.networks, gettext('New network'), gettext('Error creating network')),
            onEdit: gui.methods.typedEdit(gui.connectivity.networks, gettext('Edit network'), gettext('Error processing network')),
            onDelete: gui.methods.del(gui.connectivity.networks, gettext('Delete network'), gettext('Error deleting network')),
        });
    });
      
};