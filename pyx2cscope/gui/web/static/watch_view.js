let parameterCardEnabled = true;
let parameterRefreshInterval;
let parameterTable;

function setParameterRefreshInterval(){
    // Handle the Refresh button click
    $('#paramRefresh').click(function() {
        $.getJSON('/watch-view-update-non-live', function(data){})
        .success(parameterTable.ajax.reload());
    });

    $('#refresh1s').click(function() {
        clearInterval(parameterRefreshInterval);
        parameterRefreshInterval = setInterval(wv_periodic_update, 1000);
    });

    $('#refresh3s').click(function() {
        clearInterval(parameterRefreshInterval);
        parameterRefreshInterval = setInterval(wv_periodic_update, 3000);
    });

    $('#refresh5s').click(function() {
        clearInterval(parameterRefreshInterval);
        parameterRefreshInterval = setInterval(wv_periodic_update, 5000);
    });

    $('#refresh1s').click();
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
        $.getJSON('/watch-view-remove',
        {
            param: parameter
        },
        function(data) {
            parameterTable.ajax.reload();
        });
    });

    // update variable after loosing focus on element
    $('#parameterTable').on('blur', 'td[contenteditable="true"]', function(){
        wv_update_param(null, this);
    });

    // edit the number when on focus
    $('#parameterTable').on('keypress', 'td[contenteditable="true"]', function(e) {
        // Replace non-digit characters with an empty string
        if (e.which === 13) {
            $(this).blur(); // Remove focus from the current contenteditable element
            return false;
        }
        if ((e.which != 46 || $(this).val().indexOf('.') != -1) && (e.which < 48 || e.which > 57)) {
            return false;
        }
    });
}

function initParameterSelect(){
    $('#parameterSearch').select2({
        placeholder: "Select a variable",
        allowClear: true,
        ajax: {
            url: 'variables',
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
        $.getJSON('/watch-view-add',
        {
            param: parameter
        },
        function(data) {
            $('#parameterSearch').val(null).trigger('change');
            parameterTable.ajax.reload();
        });
    });
}

function wv_update_param(cb, element) {
    parameter = "";
    parameter_field = "";
    parameter_value = "0";
    if(element != null) { // contenteditable
        parameter = $(element).siblings()[1].textContent;
        index = $(element).index()
        parameter_field = $("#parameterTable thead>tr").children()[index].textContent;
        parameter_value = $(element).html();
    }
    if(cb != null) { // checkbox
        parameter = $(cb).parent().siblings()[0].textContent;
        parameter_field = "live";
        parameter_value = cb.checked? "1":"0";
    }
    $.getJSON('/watch-view-update',
    {
        param: parameter,
        field: parameter_field,
        value: parameter_value
    });
}

function wv_checkbox(data, type) {
    val = '<input type="checkbox" onclick="wv_update_param(this, null);"';
    if(data) val += ' checked="checked"';
    return val += '>';
}

function wv_remove(data, type){
    return '<button class="btn btn-danger remove" type="button">Remove</button>';
}

$(document).ready(function () {
    initParameterSelect();
    setParameterTableListeners();
    setParameterRefreshInterval();

    parameterTable = $('#parameterTable').DataTable({
        ajax: '/watch-view-data',
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