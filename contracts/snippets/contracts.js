$( document ).ready(function() {

    var teaser_details = document.querySelector("#data_viz_details")

    teaser_details.addEventListener("toggle", function() {
        if (teaser_details.hasAttribute("open")) {
            document.cookie = "contracts_show_teaser=opem";
        } else {
            document.cookie = "contracts_show_teaser=closed";
        }
    })
})