function getModal(identifier) {
    console.log(identifier.id);
    $.get( "/modal", { id: identifier.id } , function(data) {
        $( ".modal-container" ).append(data);
        $( ".modal-container" ).css('visibility', 'visible');
        $( ".modal-container" ).show();
    });
};

function delModal(identifier) {
    $( ".modal-container" ).hide();
    $( ".modal-container" ).empty();
}

// creates a query to the database with the relevancy
function score(pressed) {
    var data = {'relevant': this.value,
                   'query': $('#query_string')[0].value,
                   //'judge': $('#judge')[0].value,
                   'docid': $('#modal-overall #doc_id')[0].value,
                   };
    var request = $.post('/api/score', data, function (data) {
        $(pressed).css('background-color', '#00ee00');
        $('#judge-button').attr('disabled', 'true');
        }).fail(function () {
            $(pressed).css('background-color', '#ee0000');
            $(pressed).attr('disabled', 'true');
        })
};
