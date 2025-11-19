let scopeCardEnabled = true;
let scopeTable;
let scopeChart;

const socket_sv = io("/scope-view");

socket_sv.on("connect", () => {
    console.log("Connected to scope namespace:", socket_sv.id);
});

socket_sv.on("scope_table_update", (data) => {
    $('#scopeSearch').val(null).trigger('change');
    scopeTable.ajax.reload();
});

socket_sv.on("scope_chart_update", (data) => {
    // check which datasets are visible
    const visibility = {};
    scopeChart.data.datasets.forEach((ds, i) => {
      visibility[ds.label] = scopeChart.isDatasetVisible(i);
    });

    // update datasets and labels
    scopeChart.data.datasets = data.datasets;
    scopeChart.data.labels = data.labels;

    // restore visibility for matching labels
    scopeChart.data.datasets.forEach((ds, i) => {
      if (visibility[ds.label] === false) {
        scopeChart.setDatasetVisibility(i, false);
      }
    });

    // update chart
    scopeChart.update('none');
});

socket_sv.on("sample_control_updated", function(response) {
    if (response.status === "success") {
        // Handle triggerAction radio buttons
        if (response.data.triggerAction) {
            document.querySelectorAll('input[name="triggerAction"]').forEach(radio => {
                const isTarget = radio.value === response.data.triggerAction;
                radio.checked = isTarget;
                const label = document.querySelector(`label[for="${radio.id}"]`);
                label.classList.toggle('active', isTarget);
            });
        }
        // Handle sampleTime input
        if (response.data.sampleTime) {
            const sampleTimeInput = document.getElementById('sampleTime');
            sampleTimeInput.value = response.data.sampleTime;
        }
        // Handle sampleFreq input
        if (response.data.sampleFreq) {
            const sampleFreqInput = document.getElementById('sampleFreq');
            sampleFreqInput.value = response.data.sampleFreq;
        }
    } else {
        console.error("Failed to update sample control:", response.message);
    }
});

// Add this handler for the trigger control response
socket_sv.on("trigger_control_updated", function(response) {
    if (response.status === "success" && response.data) {
        // Handle trigger_mode radio buttons
        if (response.data.trigger_mode !== undefined) {
            document.querySelectorAll('input[name="trigger_mode"]').forEach(radio => {
                const isTarget = radio.value === response.data.trigger_mode.toString();
                radio.checked = isTarget;
                const label = document.querySelector(`label[for="${radio.id}"]`);
                label.classList.toggle('active', isTarget);
            });
        }
        // Handle trigger_edge radio buttons
        if (response.data.trigger_edge !== undefined) {
            document.querySelectorAll('input[name="trigger_edge"]').forEach(radio => {
                const isTarget = radio.value === response.data.trigger_edge.toString();
                radio.checked = isTarget;
                const label = document.querySelector(`label[for="${radio.id}"]`);
                label.classList.toggle('active', isTarget);
            });
        }
        // Handle trigger_level input
        if (response.data.trigger_level !== undefined) {
            const triggerLevelInput = document.getElementById('triggerLevel');
            triggerLevelInput.value = response.data.trigger_level;
        }
        // Handle trigger_delay input
        if (response.data.trigger_delay !== undefined) {
            const triggerDelayInput = document.getElementById('triggerDelay');
            triggerDelayInput.value = response.data.trigger_delay;
        }
    } else if (response.status !== "success") {
        console.error("Failed to update trigger control:", response.message);
    }
});

function initScopeSelect(){
    $('#scopeSearch').select2({
        placeholder: "Select a variable",
        dropdownAutoWidth : true,
        allowClear: true,
        ajax: {
            url: '/variables',
            dataType: 'json',
            delay: 250,
            processResults: function (data) {
                return {
                    results: data.items
                };
            },
            cache: true
        },
        minimumInputLength: 3
    });

    $('#scopeSearch').on('select2:select', function(e){
        parameter = $('#scopeSearch').select2('data')[0]['text'];
        socket_sv.emit("add_scope_var", {var: parameter});
    });
}

function setScopeTableListeners(){
    // delete Row on button click
    $('#scopeTableBody').on('click', '.remove', function () {
        parameter = $(this).parent().siblings()[2].textContent;
        socket_sv.emit("remove_scope_var", {var: parameter});
    });

    // update variable after loosing focus on element
    $('#scopeTable').on('blur', 'td[contenteditable="true"]', function(){
        sv_update_param(this);
    });

    // edit the number when on focus
    $('#scopeTable').on('keypress', 'td[contenteditable="true"]', function(e) {
        // Replace non-digit characters with an empty string
        if (e.which === 13) {
            $(this).blur(); // Remove focus from the current contenteditable element
            return false;
        }
         if ((e.which != 45 || $(this).val().indexOf('-') != -1)
            && (e.which != 46 || $(this).val().indexOf('.') != -1)
            && (e.which < 48 || e.which > 57)) {
            return false;
        }
    });
}

function sv_update_param(element) {
    parameter = $(element).closest("tr").children()[2].textContent;
    index = $(element).closest("td").index();
    parameter_field = $("#scopeTable thead>tr").children()[index].textContent;

    if(element.contentEditable == "true")
    {
        parameter_value = $(element).html();
    }
    else // checkbox, color
    {
        if(element.type == "checkbox") parameter_value = element.checked? "1":"0";
        if(element.type == "color") parameter_value = element.value;
    }

    socket_sv.emit("update_scope_var",
    {
        param: parameter,
        field: parameter_field.toLowerCase(),
        value: parameter_value
    });
}

function sv_checkbox(data, type) {
    val = '<input type="checkbox" onclick="sv_update_param(this);"';
    if(data) val += ' checked="checked"';
    return val += '>';
}

function sv_color(data, type) {
    val = '<input type="color" onchange="sv_update_param(this);"';
    val += ' value="' + data + '">';
    return val;
}

function sv_remove(data, type){
    return '<button class="btn btn-danger remove" type="button">Remove</button>';
}

const zoomOptions = {
    pan: {
        enabled: true,
        modifierKey: 'ctrl',
    },
    zoom: {
        drag: {
            enabled: true,
        },
        wheel: {
            enabled: false,
        },
        pinch: {
            enabled: true
        },
        mode: 'xy'
    }
}

const getOrCreateLegendList = (chart, id) => {
  const legendContainer = document.getElementById(id);
  let listContainer = legendContainer.querySelector('ul');

  if (!listContainer) {
    listContainer = document.createElement('ul');
    listContainer.style.display = 'flex';
    listContainer.style.flexDirection = 'row';
    listContainer.style.margin = 0;
    listContainer.style.padding = 0;

    legendContainer.appendChild(listContainer);
  }

  return listContainer;
};

const htmlLegendPlugin = {
  id: 'htmlLegend',
  afterUpdate(chart, args, options) {
    const ul = getOrCreateLegendList(chart, options.containerID);

    // Remove old legend items
    while (ul.firstChild) {
      ul.firstChild.remove();
    }

    // Reuse the built-in legendItems generator
    const items = chart.options.plugins.legend.labels.generateLabels(chart);

    items.forEach(item => {
      const li = document.createElement('li');
      li.style.alignItems = 'center';
      li.style.cursor = 'pointer';
      li.style.display = 'flex';
      li.style.flexDirection = 'row';
      li.style.marginLeft = '10px';

      li.onclick = () => {
        chart.setDatasetVisibility(
          item.datasetIndex,
          !chart.isDatasetVisible(item.datasetIndex) // toggle visibility
        );
        chart.update();
      };

      // Color box
      const boxSpan = document.createElement('span');
      boxSpan.style.background = item.fillStyle;
      boxSpan.style.borderColor = item.strokeStyle;
      boxSpan.style.borderWidth = item.lineWidth + 'px';
      boxSpan.style.display = 'inline-block';
      boxSpan.style.flexShrink = 0;
      boxSpan.style.height = '20px';
      boxSpan.style.marginRight = '10px';
      boxSpan.style.width = '20px';

      // Text
      const textContainer = document.createElement('p');
      textContainer.style.color = item.fontColor;
      textContainer.style.margin = 0;
      textContainer.style.padding = 0;

      // ✅ use chart.isDatasetVisible() instead of item.hidden
      const visible = chart.isDatasetVisible(item.datasetIndex);
      textContainer.style.textDecoration = visible ? '' : 'line-through';

      const text = document.createTextNode(item.text);
      textContainer.appendChild(text);

      li.appendChild(boxSpan);
      li.appendChild(textContainer);
      ul.appendChild(li);
    });
  }
};

function initScopeChart() {
    const chartElement = document.getElementById('scopeChart');
    const ctx = chartElement.getContext('2d');
    
    // Set the initial size of the canvas
    const container = chartElement.parentElement;
    chartElement.width = container.clientWidth;
    chartElement.height = 300; // Fixed height as per your HTML
    
    scopeChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1],
            datasets: [{
                label: 'Empty Dataset',
                data: [],
                borderColor: 'rgba(75, 192, 192, 1)',
                borderWidth: 1,
                pointRadius: 0, // Remove points for better performance
                borderJoinStyle: 'round',
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false, // This is important for fixed height
            animation: {
                duration: 0 // Disable animations for better performance
            },
            scales: {
                x: {
                    type: 'category',
                    title: {
                        display: true,
                        text: 'Time (ms)'
                    },
                    grid: {
                        display: true,
                        drawBorder: true
                    },
                    ticks: {
                        autoSkip: true,
                        includeBounds: true,
                        callback: function(value, index, ticks) {
                          const rawLabel = this.getLabelForValue(value);
                          const num = parseFloat(rawLabel);
                          if (isNaN(num)) return rawLabel;

                          const tickCount = ticks.length;
                          if (tickCount > 1000) return num.toFixed(2);
                          if (tickCount > 500) return num.toFixed(3);
                          if (tickCount > 100) return num.toFixed(4);
                          return num.toFixed(5);
                        }
                    }
                },
                y: {
                    grid: {
                        display: true,
                        drawBorder: true
                    }
                }
            },
            plugins: {
                zoom: zoomOptions,
                htmlLegend: {
                    containerID: 'legend-container',
                },
                legend: {
                    display: false
                }
            },
            elements: {
                line: {
                    borderWidth: 1.5
                }
            }
        },
        plugins: [htmlLegendPlugin],
    });
    
    // Handle window resize
    const resizeObserver = new ResizeObserver(entries => {
        const { width } = entries[0].contentRect;
        chartElement.width = width;
        scopeChart.update('none'); // Update without animation
    });
    
    resizeObserver.observe(container);

    $('#chartZoomReset').on('click', function() {
        scopeChart.resetZoom();
    });

    $('#chartExport').attr("href", "/scope-view/export")
}

function initScopeForms(){
    $("#sampleControlForm").submit(function(e) {
        e.preventDefault(); // avoid to execute the actual submit of the form.
        var formData = $(this).serialize();
        socket_sv.emit("update_sample_control", formData);
    });

    // Add change event handlers for the sample control radio buttons
    $('input[name="triggerAction"]').on('change', function() {
        // Remove active class from all labels in the same button group
        $(this).closest('.btn-group').find('.btn').removeClass('active');
        // Add active class to the clicked button's label
        $(`label[for="${this.id}"]`).addClass('active');
        
        // Submit the form
        $("#sampleControlForm").submit();
    });
    
    // Initialize the active state of the stop button on page load
    $('input[name="triggerAction"][checked]').trigger('change');

    // Handle trigger control form submission
    $("#triggerControlForm").submit(function(e) {
        e.preventDefault();
        var formData = $(this).serialize();
        socket_sv.emit("update_trigger_control", formData);
    });

    // Add change event handlers for the radio buttons to update their visual state
    $('input[name="triggerEnable"]').on('change', function() {
        // Remove active class from all labels in the same button group
        $(this).closest('.btn-group').find('.btn').removeClass('active');
        // Add active class to the clicked button's label
        $(`label[for="${this.id}"]`).addClass('active');
    });

    // Set up Save button click handler
    $("#scopeSave").on("click", function() {
        window.location.href = '/scope-view/save';
    });

    $("#scopeLoad").on("change", function(event) {
        var file = event.target.files[0];
        var formData = new FormData();
        formData.append('file', file);

        $.ajax({
            url: '/scope-view/load', // Replace with your server upload endpoint
            type: 'POST',
            data: formData,
            contentType: false,
            processData: false,
            success: function(response) {
                scopeTable.ajax.reload();
            },
            error: function(jqXHR, textStatus, errorThrown) {
                alert(jqXHR.responseJSON.msg);
            }
        }).always(function() {
            $("#scopeLoad").val("");
        });
    });
}

$(document).ready(function () {
    initScopeSelect();
    setScopeTableListeners();
    initScopeForms();
    initScopeChart();

    scopeTable = $('#scopeTable').DataTable({
        ajax: '/scope-view/data',
        searching: false,
        paging: false,
        info: false,
        responsive: true,
        columns: [
            {data: 'trigger', render: sv_checkbox, orderable: false},
            {data: 'enable', render: sv_checkbox, orderable: false},
            {data: 'variable'},
            {data: 'color', render: sv_color, orderable: false},
            {data: 'gain', orderable: false},
            {data: 'offset', orderable: false},
            {data: 'remove', render: sv_remove, orderable: false}
        ],
        columnDefs: [
            {
                targets: [4, 5],
                "createdCell": function (td, cellData, rowData, row, col) {
                    $(td).attr('contenteditable', 'true');
                }
            }
        ]
    });
});