function getModal(identifier) {
    console.log(identifier.id);
    $.get( "/modal", { id: identifier.id } , function(data) {
        console.log(data);
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
function score() {
    var request = {'relevant': this.value,
                   'query': $('#query_string')[0].value,
                   //'judge': $('#judge')[0].value,
                   'doc_id': $('#modal-overall #doc_id')[0].value,
                   };
    $.post('/api/score', request, function (data) {
        $(this).css('background-color', '#00ee00');
    });
};
