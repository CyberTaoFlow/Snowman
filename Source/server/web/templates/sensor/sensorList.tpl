
	{% csrf_token %}
	<table id="sensorList" class="sensors table table-responsive table-bordered table-hover">
		
		<thead {% if not isMain %}style="display:none;"{% endif %}>
			<tr>
				<th><input type="checkbox" id="checkbox-all" /></th>
				<th class="text-center">Name</th>
				<th class="text-center">IP-Address</th>
				<th class="text-center">Children</th>
				<th class="text-center">Status</th>
				<th class="text-center"></th>
			</tr>
		</thead>
		
		<tbody>
			{% for sensor in sensors %}
				<tr class="odd" id="{{sensor.id}}" tree-type="{% if sensor.getChildCount > 0 %}parent{% else %}child{% endif %}">
					<td><input id="checkbox" type="checkbox" name="selectSensor-{{sensor.id}}" sensor="{{sensor.id}}" /></td>
					<td class="text-center">{{sensor.name}}</td>
					<td class="text-center">{% if sensor.ipAddress == None %} {% else %}{{sensor.ipAddress}}{% endif %}</td>
					<td class="text-center"><span class="badge btn-info">{{sensor.getChildCount}}</span></td>
					<td class="text-center">
						{% if sensor.getStatus == sensor.AVAILABLE %}
							<span class="badge btn-success">Available</span>
						{% elif sensor.getStatus == sensor.UNAVAILABLE %}
							<span class="badge btn-danger">Unavailable</span>
						{% elif sensor.getStatus == sensor.INACTIVE %}
							<span class="badge btn">In-active</span>
						{% elif sensor.getStatus == sensor.AUTONOMOUS %}
							<span class="badge btn-info">Autonomous</span>
						{% elif sensor.getStatus == sensor.UNKNOWN %}
							<span class="badge btn-warning">Unknown status</span>
						{% endif %}
					</td>
					<td class="text-right">
						<div class="btn-group">
						{% if not sensor.autonomous %}
						
							<button id="regenerateSensorSecret" sid="{{sensor.id}}" class="btn btn-danger">Generate new secret</button>
						
						{% endif %}

						<button id="generateSensorRules" sid="{{sensor.id}}" class="btn btn-info">Download Ruleset</button>

						{% if sensor.getStatus == sensor.AVAILABLE %}
						
							<button id="requestUpdate" sid="{{sensor.id}}" class="btn btn-success">Request Update</button>
						
						{% endif %}
						</div>
					</td>
				</tr>
				<tr class="even" style="display:none;">
					<td colspan="6">
						{% if sensor.getChildCount > 0 %}
						<div class="panel panel-info clear">
							<div class="panel-heading"><h4>Child Sensors</h4></div>
						</div>
						{% endif %}
					</td>
				</tr>
			{% endfor %}
		</tbody>
	</table>
<!--</form>-->
