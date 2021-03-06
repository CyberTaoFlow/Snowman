<!DOCTYPE html>
{# index.tpl is the main template for the website. #} 
{# It contains the main structure of the page and loads the global static files. #}
{#  #}
<html>
<head>
	{% load staticfiles %}
	<link type="text/css" rel="stylesheet" href="{% static 'css/style.css' %}" media="screen">
	<link type="text/css" rel="stylesheet" href="{% static 'css/bootstrap/bootstrap.min.css' %}" media="screen">
	<link type="text/css" rel="stylesheet" href="{% static 'css/bootstrap/bootstrap-theme.min.css' %}" media="screen">
	<link type="text/css" rel="stylesheet" href="{% static 'css/jquery-ui/jquery-ui-1.10.4.custom.min.css' %}" media="screen">

	<script type="text/javascript" src="{% static 'js/jquery/jquery-1.11.0.min.js' %}"></script>
	<script type="text/javascript" src="{% static 'js/jquery/jquery-ui-1.10.4.custom.min.js' %}"></script>
	<script type="text/javascript" src="{% static 'js/jquery/jquery.validate.min.js' %}"></script>
	<script type="text/javascript" src="{% static 'js/bootstrap/bootstrap.min.js' %}"></script>
	<script type="text/javascript" src="{% static 'js/bootstrap/bootstrap-paginator.min.js' %}"></script>

	<script type="text/javascript" src="{% static 'js/core.js' %}"></script>
	
	<title>{% block title %} {{ title|default:"Snort Rule Manager" }} {% endblock %}</title>
</head>
<body>
	<div id="wrap" class="container no-padding">
		{% block nav %}
		{% include "general/nav.tpl" %}
		{% endblock %}
		<div id="content-wrap" class="row container">
			{% block content %}
			{% endblock %}	
		</div>
	</div>
	<div id="footer" class="container">
		{% block footer %}
		{% include "general/footer.tpl" %}
		{% endblock %}
	</div>
	<div id="console-wrapper" class="hide">
		{% block console %}
		{% include "general/console.tpl" %}
		{% endblock %}
	</div>
</body>

</html>
