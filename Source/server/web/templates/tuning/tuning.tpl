{% extends "general/index.tpl" %}
{# byRule.tpl is the main template for displaying a list of tuning objects. #} 

{% block content %}
{% load staticfiles %}
<script type="text/javascript" src="{% static 'js/tuning.js' %}"></script>
<div id="search-container" class="ruleset row col-xs-12 col-sm-102 col-md-12 pull-right">
	<div class="pull-left">
			<ul id="paginator" itemcount="{{ itemcount }}" pagelength="{{ pagelength }}" class="pagination">
				
			</ul>
		</div>
	{% csrf_token %}
	<div class="input-group col-xs-6 col-sm-6 col-md-6 col-lg-6 pull-right">
		
		<select id="searchfield" class="form-control">
			<option value="sid">SID</option>
			<option value="name">Name</option>
			<option value="sensor">Sensor Name</option>
		</select>
		<span class="input-group-btn">
			<button class="btn btn-default" type="button" id="search-button">Search</button>
		</span>
		<input id="searchtext" type="text" class="form-control">
	</div>
	<div id="tuning-buttons" class="btn-group pull-right">
		<button id="edit" type="button" class="btn btn-default" data-toggle="modal" data-target="#tuningFormModal">Edit Tuning</button>
		<button id="delete" type="button" class="btn btn-danger" data-toggle="modal" data-target="#deleteTuningModal"><span class="glyphicon glyphicon-warning-sign form-control-feedback"></span> Delete Tuning</button>
	</div>	
	
</div>
<div id="content" class="tuning col-xs-12 col-sm-12 col-md-12 well">

{% block rules %}

{% include "tuning/tuningPage.tpl" %}
		
{% endblock %}


</div>

<div class="modal fade" id="tuningFormModal" tabindex="-1" role="dialog" aria-labelledby="tuningFormModal" aria-hidden="true">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
        <h4 class="modal-title" id="tuningFormModal">Edit tuning</h4>
      </div>
      <div class="modal-body">
        <form id="tuningForm" class="form-horizontal" role="form">
        	<div id="formContent">
        
        	</div>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-default" data-dismiss="modal">Close</button>
        <button type="submit" class="btn btn-primary" id="tuning-submit" name="tuning-submit">Save changes</button>
        </form>
      </div>
    </div>
  </div>
</div>

<div class="modal fade" id="deleteTuningModal" tabindex="-1" role="dialog" aria-labelledby="deleteTuningModal" aria-hidden="true">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
		   <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
		   <h4 class="modal-title" id="deleteTuningModal">Delete Ruleset(s)</h4>
		 </div>
		<div class="modal-body">
		  <form id="deleteTuningForm" class="form-horizontal" role="form">
		  	<div id="formContent">
		  	{% csrf_token %}
		  		<div class="alert alert-danger row">
		  			<div class="col-sm-1">
		  			<span class="glyphicon glyphicon-warning-sign"></span>
		  			</div>
		  			<div class="col-sm-11">
		  				<strong>Are you absolutely sure you want to delete the Tuning? <br /><br />This cannot be reversed!</strong>
		  			</div>
		  		</div>
		  	</div>
		</div>
		<div class="modal-footer">
		  <button type="button" class="btn btn-default" data-dismiss="modal">Close</button>
		  <button type="submit" class="btn btn-danger" id="delete-submit" name="delete-submit"><span class="glyphicon glyphicon-warning-sign form-control-feedback"></span> Delete Tuning</button>
		  </form>
		</div>
      
    </div>
  </div>
</div>

{% endblock %}