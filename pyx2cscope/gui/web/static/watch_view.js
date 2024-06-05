let parameterCardEnabled = false;
let parameterRefreshInterval;
let parameterTable;

function setParameterRefreshInterval(){
    // Handle the Refresh button click
    $('#paramRefresh').click(function() {
        parameterTable.ajax.reload();
    });

    // Handle the dropdown items click
    $('#refreshNow').click(function() {
        parameterTable.ajax.reload();
    });

    $('#refresh1s').click(function() {
        clearInterval(parameterRefreshInterval);
        parameterRefreshInterval = setInterval(parameterTable.ajax.reload, 1000);
    });

    $('#refresh3s').click(function() {
        clearInterval(parameterRefreshInterval);
        parameterRefreshInterval = setInterval(parameterTable.ajax.reload, 3000);
    });

    $('#refresh5s').click(function() {
        clearInterval(parameterRefreshInterval);
        parameterRefreshInterval = setInterval(parameterTable.ajax.reload, 5000);
    });

    $('#stopRefresh').click(function() {
        clearInterval(parameterRefreshInterval);
    });
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

    // update variable after focus
    $('#parameterTable').on('blur', 'td[contenteditable="true"]', function() {
        // Call your getJSON function here
        parameter = $(this).siblings()[0].textContent;
        parameter_value = $(this).html();
        $.getJSON('/watch-view-update',
        {
            param: parameter,
            value: parameter_value
        });
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

function wv_checkbox(data, type) {
    val = '<input type="checkbox"';
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
  });


});