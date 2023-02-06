side_menu = document.getElementById("side_menu");
side_menu_width = 0;
let selecteed_node_id = 0;


// Calculate width of the side menu for a adjustment os node position
if (side_menu){
    side_menu_width = side_menu.offsetWidth;
}

$('.drag').draggable({
  appendTo: 'body',
  helper: 'clone'
});

$('#network_scheme').droppable({
  activeClass: 'active',
  hoverClass: 'hover',
  accept: ":not(.ui-sortable-helper)", // Reject clones generated by sortable
  drop: function (e, ui) {
      type = ui.draggable.prop('id')

      if (GetNetworkState() === 3){
          return;
      }

      // We add new device. Drop the network state.
      if (GetNetworkState()){
        SetNetworkRunButtonState(0, null);
      }

      if (type === 'host'){
          node_id = HostUid();
          nodes.push(
              {
                  data: {id: node_id, label: node_id},
                  renderedPosition: {x: ui.position.left - side_menu_width, y: ui.position.top},
                  classes: ['host'],
                  config: {
                      type: 'host',
                      label: node_id,
                  },
                  interface: [],
              }
          );

          // post new nodes to the server
          PostNodes();
          DrawGraph(nodes, edges);
          return;
      }

      if (type === 'l2_switch'){
          node_id = l2SwitchUid();
          nodes.push(
              {
                  data: {id: node_id, label: node_id},
                  renderedPosition: {x: ui.position.left - side_menu_width, y: ui.position.top},
                  classes: ['l2_switch'],
                  config: {
                      type: 'l2_switch',
                      label: node_id,
                  },
                  interface: [],
              }
          );

          PostNodes();
          DrawGraph(nodes, edges);
          return;
      }

      if (type === 'l1_hub'){
          node_id = l1HubUid();

          nodes.push(
              {
                  data: {id: node_id, label: node_id},
                  renderedPosition: {x: ui.position.left - side_menu_width, y: ui.position.top},
                  classes: ['l1_hub'],
                  config: {
                      type: 'l1_hub',
                      label: node_id,
                  },
                  interface: [],
              }
          );

          PostNodes();
          DrawGraph(nodes, edges);
          return;
      }
  }
});

$('#NetworkRunButton').click(function() {

    // Run simulating
    if (GetNetworkState() === 0)
    {
        // Check for job. If no job - show modal and exit.
        if (!jobs.length)
        {
            $('#noJobsModal').modal('toggle');
            return;
        }

        $(this).text('Симуляция');
        $(this).removeClass('btn-primary');
        $(this).addClass('btn-secondary');
        $(this).prop('disabled', true);

        RunSimulation(network_guid);
        SetNetworkState(1);
        return;
    }

    // Network in running
    if (GetNetworkState() === 2) {

        // Do we got a packets?
        if (!packets){
            console.log("Don't have a packets");
            return;
        }

        $(this).text('Стоп');
        $(this).removeClass('btn-success');
        $(this).addClass('btn-danger');

        SetNetworkState(3);
        DrawGraphStatic(nodes, edges, packets);
        return;
    }

    if (GetNetworkState() === 3)
    {

        let timeout_last_id = window.setTimeout(function () {
        }, 0);

        while (timeout_last_id--) {
            window.clearTimeout(timeout_last_id); // will do nothing if no timeout with id is present
        }

        // Do we got a packets?
        if (!packets){
            $(this).text('Симулировать');
            $(this).removeClass('btn-danger');
            $(this).addClass('btn-primary');

            SetNetworkState(0);
            return;
        }

        $(this).text('Запустить');
        $(this).removeClass('btn-danger');
        $(this).removeClass('btn-secondary');
        $(this).addClass('btn-success');

        DrawGraph(nodes, edges);
        SetNetworkState(2);
        return;
    }
})

$('#NetworkSharedRunButton').click(function() {

    // Network in running
    if (GetNetworkState() === 2) {

        // Do we got a packets?
        if (!packets){
            console.log("Don't have a packets");
            return;
        }

        $(this).text('Стоп');
        $(this).removeClass('btn-success');
        $(this).addClass('btn-danger');

        SetNetworkState(3);
        DrawGraphStatic(nodes, edges, packets);
        return;
    }

    if (GetNetworkState() === 3)
    {

        let timeout_last_id = window.setTimeout(function () {
        }, 0);

        while (timeout_last_id--) {
            window.clearTimeout(timeout_last_id); // will do nothing if no timeout with id is present
        }

        // Do we got a packets?
        if (!packets){
            $(this).text('Симулировать');
            $(this).removeClass('btn-danger');
            $(this).addClass('btn-primary');

            SetNetworkState(0);
            return;
        }

        $(this).text('Запустить');
        $(this).removeClass('btn-danger');
        $(this).removeClass('btn-secondary');
        $(this).addClass('btn-success');

        DrawSharedGraph(nodes, edges);
        SetNetworkState(2);
        return;
    }
})