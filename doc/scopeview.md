## ScopeView
1. To use the scope functionality, add channel to the scope: **add_scope_channel(variable: Variable)** : 
```
x2cScope.add_scope_channel(variable1)
x2cScope.add_scope_channel(variable2)
```
2. To remove channel: **remove_scope_channel(variable: Variable)**:
```
x2cScope.remove_scope_channel(variable2)
```
3. Up to 8 channels can be added. 
4. To Set up Trigger, any available variable can be selected, by default works on no trigger configuration.
```
x2cscope.set_scope_trigger(variable: Variable, trigger_level: int, trigger_mode: int, trigger_delay: int, trigger_edge: int)
```
5. ##### Trigger Parameters:
```
srcChannel: TriggerChannel (variable)
Level: trigger_level
Trigger_mode: 1 for triggered, 0 for Auto (No trigger)
Trigger_delay = Value > 0 Pre-trigger, Value < 0 Post trigger
Trigger_Edge: Rising (1) or Falling (0)
```

```
x2cScope.set_scope_trigger(variable3, trigger_level=500, trigger_mode=1, trigger_delay=50, trigger_edge=1)
```

6. ##### **clear_trigger()**: Clears and diable trigger
```
x2cscope.clear_trigger()
```
7. #### set_sample_time(sample_time: int): 
This paramater defines a pre-scaler when the scope is in the sampling mode. This can be used to extend total sampling time at cost of resolution. 0 = every sample, 1 = every 2nd sample, 2 = every 3rd sample .....
```
x2cScope.set_sample_time(2)
```
8. #### is_scope_data_ready(self) -> bool: 
Returns Scope sampling state. Returns: true if sampling has completed, false if it’s yet in progress.  
```
while not x2cScope.is_scope_data_ready():
    time.sleep(0.1)
```
9. #### get_scope_channel_data(valid_data=False) -> Dict[str, List[Number]]: 
Once sampling is completed, this function could be used to get the sampled data.
```
data = x2cScope.get_scope_channel_data()
```
