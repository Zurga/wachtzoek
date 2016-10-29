$(document).ready(function(){
    $("button.c-pagination__page").click(function() {
        var number = $(this).text();
        var input = $("<input>")
               .attr("type", "hidden")
               .attr("name", "current_page").val(number);
        $('form').append($(input));
        
        $('form').submit();
    });
});
