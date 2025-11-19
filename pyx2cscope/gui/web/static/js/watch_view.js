let parameterCardEnabled = true;
let parameterTable;

const socket_wv = io("/watch-view");

socket_wv.on("connect", () => {
    console.log("Connected to watch namespace:", socket_wv.id);
});

socket_wv.on("watch_data_update", (data) => {
    console.log("Update from server:", data);
    parameterTable.rows().every(function() {
        const rowData = this.data();
        const updatedVar = data.find(item => item.variable === rowData.variable);

        if (updatedVar) {
            // Update the row data with new values
            Object.assign(rowData, updatedVar);
            // Redraw the row with updated data
            this.data(rowData).draw(false); // false means don't reset paging
        }
    });
});

socket_wv.on("watch_table_update", (data) => {
    $('#parameterSearch').val(null).trigger('change');
    console.log("contents of table have changed:", data);
    parameterTable.ajax.reload();
});


function setParameterRefreshInterval(){
    // Handle the Refresh button click
    $('#paramRefresh').click(function() {
        socket_wv.emit("refresh_watch_data");
    });

    // Handle refresh rate buttons with data attributes
    $('.refresh-rate-btn').click(function() {
        const rate = $(this).data('rate');
        if (rate) {
            socket_wv.emit("set_watch_rate", { rate: rate });
        }
    });
}

function wv_periodic_update(){
    if(!parameterCardEnabled) return;
    update = false;
    cbs = $('td:first-child input:checkbox', $('#parameterTableBody'));
    for(let cb of cbs) {
        update |= cb.checked?1:0;
    }
    if(update) parameterTable.ajax.reload();
}

function setParameterTableListeners(){
    // delete Row on button click
    $('#parameterTableBody').on('click', '.remove', function () {
        parameter = $(this).parent().siblings()[1].textContent;
        socket_wv.emit("remove_watch_var", {var: parameter});
    });

    // update variable after loosing focus on element
    $('#parameterTable').on('blur', 'td[contenteditable="true"]', function(){
        wv_update_param(this);
    });

    // edit the number when on focus
    $('#parameterTable').on('keypress', 'td[contenteditable="true"]', function(e) {
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

    // Set up Save button click handler
    $("#parameterSave").on("click", function() {
        window.location.href = '/watch-view/save';
    });
    $('#parameterLoad').on('change', function(event) {
        var file = event.target.files[0];
        var formData = new FormData();
        formData.append('file', file);

        $.ajax({
            url: '/watch-view/load', // Replace with your server upload endpoint
            type: 'POST',
            data: formData,
            contentType: false,
            processData: false,
            success: function(response) {
                parameterTable.ajax.reload();
            },
            error: function(jqXHR, textStatus, errorThrown) {
                alert(jqXHR.responseJSON.msg);
            }
        }).always(function() {
            $('#parameterLoad').val('');
        });
    });
}

function initParameterSelect(){
    $('#parameterSearch').select2({
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

    $('#parameterSearch').on('select2:select', function(e){
        parameter = $('#parameterSearch').select2('data')[0]['text'];
        socket_wv.emit("add_watch_var", {var: parameter});
    });
}

function wv_update_param(element) {
    parameter = $(element).closest("tr").children()[1].textContent;
    index = $(element).closest("td").index();
    parameter_field = $("#parameterTable thead>tr").children()[index].textContent;

    if(element.contentEditable == "true")
    {
        parameter_value = $(element).html();
    }
    else // checkbox, color
    {
        if(element.type == "checkbox") parameter_value = element.checked? "1":"0";
    }
    socket_wv.emit("update_watch_var",
    {
        param: parameter,
        field: parameter_field.toLowerCase(),
        value: parameter_value
    });
}

function wv_checkbox(data, type) {
    val = '<input type="checkbox" onclick="wv_update_param(this);"';
    if(data) val += ' checked="checked"';
    return val += '>';
}

function wv_remove(data, type){
    return '<button class="btn btn-danger remove float-end" type="button">Remove</button>';
}

$(document).ready(function () {
    initParameterSelect();
    setParameterTableListeners();
    setParameterRefreshInterval();

    parameterTable = $('#parameterTable').DataTable({
        ajax: '/watch-view/data',
        searching: false,
        paging: false,
        info: false,
        columns: [
            {data: 'live', render: wv_checkbox},
            {data: 'variable'},
            {data: 'type'},
            {data: 'value', orderable: false},
            {data: 'scaling', orderable: false},
            {data: 'offset', orderable: false},
            {data: 'scaled_value', orderable: false},
            {data: 'remove', render: wv_remove, orderable: false}
        ],
        columnDefs: [
            {
                targets: [3, 4, 5],
                "createdCell": function (td, cellData, rowData, row, col) {
                    $(td).attr('contenteditable', 'true');
                }
            }
        ]
    });
});