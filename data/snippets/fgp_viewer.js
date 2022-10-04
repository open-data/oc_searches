var i18n = {
    "OGSCart_empty": {
        "en": "Map List is Empty",
        "fr": "La liste est vide"
    },
    "OGSCart_full": {
        "en": "Map List is full",
        "fr": "La liste est plein"
    },
    "OGSCart_has": {
        "en": "Map List",
        "fr": "Liste de Cartes"
    },
    "OGSCart_of": {
        "en": "of",
        "fr": "de"
    }
}

/* Peter-Paul Koch for these cookie functions (http://www.quirksmode.org/js/cookies.html) */

function createCookie(name,value,days) {
    var expires = "";
    if (days) {
        var date = new Date();
        date.setTime(date.getTime()+(days*24*60*60*1000));
        expires = "; expires="+date.toGMTString();
    }
    document.cookie = name+"="+value+expires+"; Secure; SameSite=Strict; path=/";
}

function readCookie(name) {
    var nameEQ = name + "=";
    var ca = document.cookie.split(';');
    for(var i=0;i < ca.length;i++) {
        var c = ca[i];
        while (c.charAt(0)==' ') c = c.substring(1,c.length);
        if (c.search(nameEQ) == 0) return decodeURIComponent(c.substring(nameEQ.length,c.length));
    }
    return null;
}

function eraseCookie(name) { createCookie(name,"",-1) }

var OGSMapsMaxCart = 5;
var OGSMapsChecked_ids = [];

// Low cost sanity functions
function uniqueArray(){ OGSMapsChecked_ids = $.grep(OGSMapsChecked_ids, function(v, k){ return $.inArray(v ,OGSMapsChecked_ids) === k; }); }
function cleanCart()
{
    // Duplicates?
    uniqueArray();

    // Blanks?
    var index = OGSMapsChecked_ids.indexOf('');
    if(index > -1) { OGSMapsChecked_ids.splice(index,1); }

    // Adapt for the cookie
    if(OGSMapsChecked_ids.length === 0)
    { OGSMapsChecked_ids = [] }

    if(OGSMapsChecked_ids.length === 0)
    {
        $(".ogscartwrapper").hide()
        $(".ogscartwrapper").attr("disabled", "disabled");
        $(".ogscartwrapper").css({"visibility":"hidden"});
    }
    else
    {
        $(".ogscartwrapper").removeAttr("disabled");
        $(".ogscartwrapper").css({"visibility":"visible"});
        $(".ogscartwrapper").show()
    }
}

function updateCartUI()
{
    var solr_query = '';
    cleanCart();
    // Only accept en and fr as languages
    if (wb.lang == 'fr') {
        solr_query = '/search/fr/data/?search_text="' + OGSMapsChecked_ids.join('" OR "') + '"'
    } else {
        solr_query = '/search/en/data/?search_text="' + OGSMapsChecked_ids.join('" OR "') + '"'
    }
    $('.ogscartlistbtn').attr("href", solr_query);

    cart_full = false
    if(OGSMapsChecked_ids.length === 0)
    {
        $(".ogscartlistbtn").hide();
        $(".ogscartplotbtn").hide();
        // IE 9 adaptation, can't hide them so we disable
        $(".ogscartlistbtn").attr("disabled", "disabled");
        $(".ogscartplotbtn").attr("disabled", "disabled");
        $(".ogscarttally").text(' '+i18n["OGSCart_empty"][wb.lang]);
    }
    else if(OGSMapsChecked_ids.length >= OGSMapsMaxCart)
    {
        // IE 9 adaptation, can't hide them so we disable
        $(".ogscartlistbtn").removeAttr("disabled");
        $(".ogscartplotbtn").removeAttr("disabled");
        $(".ogscartlistbtn").show();
        $(".ogscartplotbtn").show();
        $(".ogscarttally").text(' '+i18n["OGSCart_full"][wb.lang]);
        cart_full = true
    }
    else
    {
        // IE 9 adaptation, can't hide them so we disable
        $(".ogscartlistbtn").removeAttr("disabled");
        $(".ogscartplotbtn").removeAttr("disabled");
        $(".ogscartlistbtn").show()
        $(".ogscartplotbtn").show()
        $(".ogscarttally").text(' '+i18n["OGSCart_has"][wb.lang]+' ('+OGSMapsChecked_ids.length+' '+i18n["OGSCart_of"][wb.lang]+' '+OGSMapsMaxCart+')');
    }

    $(".ogscartbtn").each(function() {
        var action = $(this).attr('id').split('_');
        var type = action[0];
        var id = action[1];

        var cart_has = false;
        if(OGSMapsChecked_ids.indexOf(id) > -1) { cart_has = true; }

        if(type == 'OGSCartAdd')
        {
            if(cart_has)
            {
                $(this).hide();
                // IE 9 adaptation, can't hide them so we disable
                $(this).attr("disabled", "disabled");
            }
            else if(cart_full)
            {
                $(this).hide();
                // IE 9 adaptation, can't hide them so we disable
                $(this).attr("disabled", "disabled");
            }
            else
            {
                // IE 9 adaptation, can't hide them so we disable
                $(this).removeAttr("disabled");
                $(this).show();
            }
        }
        else if(type == 'OGSCartRemove')
        {
            if(cart_has)
            {
                $(this).show();
                // IE 9 adaptation, can't hide them so we disable
                $(this).removeAttr("disabled");
            }
            else
            {
                $(this).hide();
                // IE 9 adaptation, can't hide them so we disable
                $(this).attr("disabled", "disabled");
            }
        }
    });
}

// Cart setup
function initCart()
{
    var OGSMapsShoppingCart_cookie = readCookie('OGSMapsCookie_cart');
    if (OGSMapsShoppingCart_cookie != null)
    { OGSMapsChecked_ids = OGSMapsShoppingCart_cookie.split(',') }
    cleanCart();
}

function saveCart()
{
    cleanCart();
    eraseCookie('OGSMapsCookie_cart');
    if (OGSMapsChecked_ids.length > 0)
    { createCookie('OGSMapsCookie_cart',OGSMapsChecked_ids.join(','),30) }
}

function addCartItem(id)
{
    if (OGSMapsChecked_ids.length >= OGSMapsMaxCart)
    {
        alert("The cart can only hold "+OGSMapsMaxCart+" datasets");
        $(this).attr('checked', false);
    }
    else
    { OGSMapsChecked_ids.push(id) }
    saveCart()
}

// This is required for cart management links
function removeCartItem(id)
{
    var index = jQuery.inArray(id,OGSMapsChecked_ids);
    if(index !== -1) { OGSMapsChecked_ids.splice(index, 1) }
    eraseCookie('OGSMapsCookie_cart');
    saveCart()
}

// Part UI ease of use and part system reset
function dumpCart()
{
    OGSMapsChecked_ids = [];
    saveCart()
}

// Initiate ramp displaying cart items
function viewOnMap()
{
    if(OGSMapsChecked_ids.length === 0)
    { alert('Select an item to view on RAMP first') }
    else
    {
        location.href=OGSRoot+OGSMapsChecked_ids.join(',')
    }
}

var OGSMapsCart_lang = 'en'
{% if LANGUAGE_CODE == 'fr' %}
var OGSRoot = '{{ od_fr_fgp_root }}'
{% else %}
var OGSRoot = '{{ od_en_fgp_root }}'
{% endif %}


$( document ).ready(function() {
  wb.lang = '{{ language }}';
  initCart()
  updateCartUI()

  $("#OGSCartPlotItems").click(function() {
    viewOnMap()
  });

  // Part UI ease of use and part system reset
  $("#OGSCartDumpItems").click(function() {
    dumpCart()
    updateCartUI()
  });

  $(".ogscartviewbtn").click(function() {
    var action = $(this).attr('id').split('_')
    type = action[0]
    id = action[1]

    location.href='{% if LANGUAGE_CODE == 'fr' %}{{ od_fr_fgp_root }}{% else %}{{ od_en_fgp_root }}{% endif %}'+id
    return false
  });

  $(".ogscartbtn").click(function() {
    var action = $(this).attr('id').split('_')
    type = action[0]
    id = action[1]

    // Action
    if(type == 'OGSCartAdd')    { addCartItem(id)    }
    if(type == 'OGSCartRemove') { removeCartItem(id) }
    updateCartUI()
  });

  // Changes to the cart in another tab/window should be accounted for
  $(window).focus(function() {
    initCart()
    updateCartUI()
  });

<!-- End Cart -->

});
