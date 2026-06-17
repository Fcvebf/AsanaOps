import argparse
import pandas as pd
import asana
import os
import asana
from asana.configuration import Configuration
from asana.api_client import ApiClient
from asana.api.users_api import UsersApi
from asana.api.sections_api import SectionsApi
from asana.api.workspaces_api import WorkspacesApi
from asana.api.portfolios_api import PortfoliosApi
from asana.api.projects_api import ProjectsApi
import json
import pandas as pd
import urllib3
import os

urllib3.disable_warnings()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# === CONFIG ===
with open(".env") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#"):
            key, value = line.split("=", 1)
            os.environ[key] = value

ASANA_TOKEN = os.getenv("ASANA_TOKEN") 
WORKSPACE_ID= os.getenv("WORKSPACE_ID") 
PROJECT_ID = os.getenv("PROJECT_ID") 
SECTION_ID = os.getenv("SECTION_ID") 

api_client=None



def build_asana_custom_fields(project_json, excel_row):
    """
    Parameters
    ----------
    project_json : str | dict
        The ASANA project JSON string (or already parsed dict)

    excel_row : dict | pandas.Series
        One row from the Excel file

    Returns
    -------
    dict
        Dictionary ready for ASANA custom_fields
    """

    # Parse JSON string if needed
    if isinstance(project_json, str):
        project_data = json.loads(project_json)
    else:
        project_data = project_json

    result = {}

    # Build quick lookup:
    # field_name -> custom_field object
    field_map = {}

    for setting in project_data.get("custom_field_settings", []):
        cf = setting.get("custom_field", {})
        field_name = cf.get("name")

        if field_name:
            field_map[field_name] = cf

    # Iterate through Excel row columns
    for column_name, raw_value in excel_row.items():

        # Skip NaN / empty values
        if pd.isna(raw_value) or str(raw_value).strip() == "":
            continue

        # Check if this Excel column exists as ASANA custom field
        if column_name not in field_map:
            continue

        custom_field = field_map[column_name]

        field_gid = custom_field.get("gid")
        field_type = custom_field.get("type")

        # -------------------------
        # TEXT / DATE / OTHER TYPES
        # -------------------------
        if field_type != "enum":
            if(field_type=="date"):
                new_date='{"date":""}'                
                result[field_gid] = "" if pd.isna(raw_value) else pd.to_datetime(raw_value).date().isoformat()
                result[field_gid]={"date": result[field_gid]}                
            else:
                result[field_gid] = str(raw_value)

        # -------------------------
        # ENUM TYPE
        # -------------------------
        else:
            excel_value = str(raw_value).strip()

            matched_option_gid = None

            for option in custom_field.get("enum_options", []):

                option_name = option.get("name", "").strip()

                if option_name.lower() == excel_value.lower():
                    matched_option_gid = option.get("gid")
                    break

            # Only add if match found
            if matched_option_gid:
                result[field_gid] = matched_option_gid

    return result


def create_project_task(projects_api_instance,tasks_api_instance,sections_api_instance,workspace_id, project_id, row,project_sections: pd.DataFrame):
    section_name = row.get("Section", '')
    section_id=project_sections.loc[project_sections["name"] == section_name,"gid"].iloc[0]
    task_name = row.get("Name", '')
    due_date = "" if pd.isna(row.get("Due Date")) else pd.to_datetime(row.get("Due Date")).date().isoformat()
    
    print("-------------------------------------------------------------")
    print(f"Creating task:{section_name}-{task_name}")
    proj_customfields_df,proj_customfields_json=list_project_customfields(projects_api_instance,project_id,False)
    #print(proj_customfields_df)
   
    task_custfields_dict=build_asana_custom_fields(proj_customfields_json,row)

    body = {"data":  {
        "workspace":workspace_id,
        "projects":project_id,
        "name": task_name,
        "due_on":due_date,
        "custom_fields":task_custfields_dict,     
    }}
    opts = {
    'opt_fields': "actual_time_minutes,approval_status,assigned_by,assigned_by.name,assignee,assignee.name,assignee_section,assignee_section.name,assignee_status,completed,completed_at,completed_by,completed_by.name,created_at,created_by,custom_fields,custom_fields.asana_created_field,custom_fields.created_by,custom_fields.created_by.name,custom_fields.currency_code,custom_fields.custom_label,custom_fields.custom_label_position,custom_fields.date_value,custom_fields.date_value.date,custom_fields.date_value.date_time,custom_fields.default_access_level,custom_fields.description,custom_fields.display_value,custom_fields.enabled,custom_fields.enum_options,custom_fields.enum_options.color,custom_fields.enum_options.enabled,custom_fields.enum_options.name,custom_fields.enum_value,custom_fields.enum_value.color,custom_fields.enum_value.enabled,custom_fields.enum_value.name,custom_fields.format,custom_fields.has_notifications_enabled,custom_fields.id_prefix,custom_fields.input_restrictions,custom_fields.is_formula_field,custom_fields.is_global_to_workspace,custom_fields.is_value_read_only,custom_fields.multi_enum_values,custom_fields.multi_enum_values.color,custom_fields.multi_enum_values.enabled,custom_fields.multi_enum_values.name,custom_fields.name,custom_fields.number_value,custom_fields.people_value,custom_fields.people_value.name,custom_fields.precision,custom_fields.privacy_setting,custom_fields.reference_value,custom_fields.reference_value.name,custom_fields.representation_type,custom_fields.resource_subtype,custom_fields.text_value,custom_fields.type,custom_type,custom_type.name,custom_type_status_option,custom_type_status_option.name,dependencies,dependents,due_at,due_on,external,external.data,followers,followers.name,hearted,hearts,hearts.user,hearts.user.name,html_notes,is_rendered_as_separator,liked,likes,likes.user,likes.user.name,memberships,memberships.project,memberships.project.name,memberships.section,memberships.section.name,modified_at,name,notes,num_hearts,num_likes,num_subtasks,parent,parent.created_by,parent.name,parent.resource_subtype,permalink_url,projects,projects.name,resource_subtype,start_at,start_on,tags,tags.name,workspace,workspace.name", # list[str] | This endpoint returns a resource which excludes some properties by default. To include those optional properties, set this query parameter to a comma-separated list of the properties you wish to include.
    }
    #print(body)
    
    try:
        # Create task
        create_task_response = tasks_api_instance.create_task(body,opts)
        #print(create_task_response)
        #print(create_task_response.get("gid"))

        # Move to section (if defined)
        if section_id:            
            print(f"Moving task to section:{section_id}")
            opts = {'body': {"data": {"task":create_task_response.get("gid")}}}
            sections_api_instance.add_task_for_section(section_id,opts)

        print(f"✅ Created task: {task_name}")

    except Exception as e:
        print(f"❌ Failed to create task: {create_task_response.get("name")}")
        print(e)
    


def get_custom_field_value(custom_fields, field_name):
    for field in custom_fields:
        if field.get("name") == field_name:
            return field.get("display_value")
    return None


def list_tasks_in_project(api_client,project_id,custom_fields=[],section_id=None):
    
    print(f"Calling list_tasks_in_project for  project id: {project_id}")
    tasks_api_instance = asana.TasksApi(api_client)
    opts = {
       'limit': 100, # int | Results per page. The number of objects to return per page. The value must be between 1 and 100.
        'opt_fields': "actual_time_minutes,approval_status,assigned_by,assigned_by.name,assignee,assignee.name,assignee_section,assignee_section.name,assignee_status,completed,completed_at,completed_by,completed_by.name,created_at,created_by,custom_fields,custom_fields.asana_created_field,custom_fields.created_by,custom_fields.created_by.name,custom_fields.currency_code,custom_fields.custom_label,custom_fields.custom_label_position,custom_fields.date_value,custom_fields.date_value.date,custom_fields.date_value.date_time,custom_fields.default_access_level,custom_fields.description,custom_fields.display_value,custom_fields.enabled,custom_fields.enum_options,custom_fields.enum_options.color,custom_fields.enum_options.enabled,custom_fields.enum_options.name,custom_fields.enum_value,custom_fields.enum_value.color,custom_fields.enum_value.enabled,custom_fields.enum_value.name,custom_fields.format,custom_fields.has_notifications_enabled,custom_fields.id_prefix,custom_fields.input_restrictions,custom_fields.is_formula_field,custom_fields.is_global_to_workspace,custom_fields.is_value_read_only,custom_fields.multi_enum_values,custom_fields.multi_enum_values.color,custom_fields.multi_enum_values.enabled,custom_fields.multi_enum_values.name,custom_fields.name,custom_fields.number_value,custom_fields.people_value,custom_fields.people_value.name,custom_fields.precision,custom_fields.privacy_setting,custom_fields.reference_value,custom_fields.reference_value.name,custom_fields.representation_type,custom_fields.resource_subtype,custom_fields.text_value,custom_fields.type,custom_type,custom_type.name,custom_type_status_option,custom_type_status_option.name,dependencies,dependents,due_at,due_on,external,external.data,followers,followers.name,hearted,hearts,hearts.user,hearts.user.name,html_notes,is_rendered_as_separator,liked,likes,likes.user,likes.user.name,memberships,memberships.project,memberships.project.name,memberships.section,memberships.section.name,modified_at,name,notes,num_hearts,num_likes,num_subtasks,offset,parent,parent.created_by,parent.name,parent.resource_subtype,path,permalink_url,projects,projects.name,resource_subtype,start_at,start_on,tags,tags.name,uri,workspace,workspace.name", # list[str] | This endpoint returns a resource which excludes some properties by default. To include those optional properties, set this query parameter to a comma-separated list of the properties you wish to include.
    }
    
    try:
        # Get tasks from a project
        api_response = tasks_api_instance.get_tasks_for_project(project_id, opts)
        #print(api_response)
        
        results=[]
        for data in api_response:
            if (pd.isna(section_id)):
                results.append(data)
            else:
                task_section_id=data.get("memberships", [{}])[0].get("section", {}).get("gid")
                if (task_section_id == section_id):
                    results.append(data)

            #print("-"*50)
            #print(data)            
            #print(data.get('name')+","+data.get('notes')+","+data.get("created_at")+","+ str(data.get('due_at') or ''))
        df = pd.DataFrame(results)
        #print(df.columns.tolist())
        pd.set_option("display.max_columns", None)
        pd.set_option("display.max_rows", None)
        pd.set_option("display.max_colwidth", None)
        
        if(len(df)>0):
            df["section_name"] = df["memberships"].apply(lambda x: x[0]["section"]["name"] if x and "section" in x[0] else None)
        
            for field in custom_fields:            
                df[field] = df["custom_fields"].apply(lambda x: get_custom_field_value(x, field))            

            # Print result
            print(df[["section_name","name","gid"]+custom_fields].sort_values(by="section_name").reset_index(drop=True))
        else:
            print("No tasks in project!")    
    except Exception as e:
        print("Exception when calling TasksApi->get_tasks_for_project: %s\n" % e)



def list_project_sections(api_client,project_id,printOutput=True):
    if printOutput:
        print(f"Calling list_project_sections for  project id: {project_id}")
    sections_api_instance = asana.SectionsApi(api_client)
    opts = {
    'limit': 100, # int | Results per page. The number of objects to return per page. The value must be between 1 and 100.
    'opt_fields': "actual_time_minutes,approval_status,assigned_by,assigned_by.name,assignee,assignee.name,assignee_section,assignee_section.name,assignee_status,completed,completed_at,completed_by,completed_by.name,created_at,created_by,custom_fields,custom_fields.asana_created_field,custom_fields.created_by,custom_fields.created_by.name,custom_fields.currency_code,custom_fields.custom_label,custom_fields.custom_label_position,custom_fields.date_value,custom_fields.date_value.date,custom_fields.date_value.date_time,custom_fields.default_access_level,custom_fields.description,custom_fields.display_value,custom_fields.enabled,custom_fields.enum_options,custom_fields.enum_options.color,custom_fields.enum_options.enabled,custom_fields.enum_options.name,custom_fields.enum_value,custom_fields.enum_value.color,custom_fields.enum_value.enabled,custom_fields.enum_value.name,custom_fields.format,custom_fields.has_notifications_enabled,custom_fields.id_prefix,custom_fields.input_restrictions,custom_fields.is_formula_field,custom_fields.is_global_to_workspace,custom_fields.is_value_read_only,custom_fields.multi_enum_values,custom_fields.multi_enum_values.color,custom_fields.multi_enum_values.enabled,custom_fields.multi_enum_values.name,custom_fields.name,custom_fields.number_value,custom_fields.people_value,custom_fields.people_value.name,custom_fields.precision,custom_fields.privacy_setting,custom_fields.reference_value,custom_fields.reference_value.name,custom_fields.representation_type,custom_fields.resource_subtype,custom_fields.text_value,custom_fields.type,custom_type,custom_type.name,custom_type_status_option,custom_type_status_option.name,dependencies,dependents,due_at,due_on,external,external.data,followers,followers.name,hearted,hearts,hearts.user,hearts.user.name,html_notes,is_rendered_as_separator,liked,likes,likes.user,likes.user.name,memberships,memberships.project,memberships.project.name,memberships.section,memberships.section.name,modified_at,name,notes,num_hearts,num_likes,num_subtasks,offset,parent,parent.created_by,parent.name,parent.resource_subtype,path,permalink_url,projects,projects.name,resource_subtype,start_at,start_on,tags,tags.name,uri,workspace,workspace.name", # list[str] | This endpoint returns a resource which excludes some properties by default. To include those optional properties, set this query parameter to a comma-separated list of the properties you wish to include.
    }

    try:
        # Get tasks from a project
        api_response = sections_api_instance.get_sections_for_project(project_id, opts)        
        results=[]   
        for data in api_response:    \
            results.append(data)
            #print("------------------------")
            #print(data)
            #print(data.get('name')+","+data.get('notes')+","+data.get("created_at")+","+ str(data.get('due_at') or ''))
        df = pd.DataFrame(results)
        if printOutput:
            print(df[["name","gid"]])           
        return df
    except Exception as e:
        print("Exception when calling TasksApi->get_tasks_for_project: %s\n" % e)




def extract_custom_fields(data, results=None):
    results = []    
    #print(data)
    results = [
    {
        "gid": item["custom_field"]["gid"],
        "name": item["custom_field"]["name"],
        "type": item["custom_field"]["type"]
    }   for item in data.get("custom_field_settings", [])]

    return results



def list_project_customfields(projects_api_instance,project_id,printOutput=True):
         
    opts = {
        #'opt_fields': "archived,color,completed,completed_at,completed_by,completed_by.name,created_at,created_from_template,created_from_template.name,current_status,current_status.author,current_status.author.name,current_status.color,current_status.created_at,current_status.created_by,current_status.created_by.name,current_status.html_text,current_status.modified_at,current_status.text,current_status.title,current_status_update,current_status_update.resource_subtype,current_status_update.title,custom_field_settings,custom_field_settings.custom_field,custom_field_settings.custom_field.asana_created_field,custom_field_settings.custom_field.created_by,custom_field_settings.custom_field.created_by.name,custom_field_settings.custom_field.currency_code,custom_field_settings.custom_field.custom_label,custom_field_settings.custom_field.custom_label_position,custom_field_settings.custom_field.date_value,custom_field_settings.custom_field.date_value.date,custom_field_settings.custom_field.date_value.date_time,custom_field_settings.custom_field.default_access_level,custom_field_settings.custom_field.description,custom_field_settings.custom_field.display_value,custom_field_settings.custom_field.enabled,custom_field_settings.custom_field.enum_options,custom_field_settings.custom_field.enum_options.color,custom_field_settings.custom_field.enum_options.enabled,custom_field_settings.custom_field.enum_options.name,custom_field_settings.custom_field.enum_value,custom_field_settings.custom_field.enum_value.color,custom_field_settings.custom_field.enum_value.enabled,custom_field_settings.custom_field.enum_value.name,custom_field_settings.custom_field.format,custom_field_settings.custom_field.has_notifications_enabled,custom_field_settings.custom_field.id_prefix,custom_field_settings.custom_field.input_restrictions,custom_field_settings.custom_field.is_formula_field,custom_field_settings.custom_field.is_global_to_workspace,custom_field_settings.custom_field.is_value_read_only,custom_field_settings.custom_field.multi_enum_values,custom_field_settings.custom_field.multi_enum_values.color,custom_field_settings.custom_field.multi_enum_values.enabled,custom_field_settings.custom_field.multi_enum_values.name,custom_field_settings.custom_field.name,custom_field_settings.custom_field.number_value,custom_field_settings.custom_field.people_value,custom_field_settings.custom_field.people_value.name,custom_field_settings.custom_field.precision,custom_field_settings.custom_field.privacy_setting,custom_field_settings.custom_field.reference_value,custom_field_settings.custom_field.reference_value.name,custom_field_settings.custom_field.representation_type,custom_field_settings.custom_field.resource_subtype,custom_field_settings.custom_field.text_value,custom_field_settings.custom_field.type,custom_field_settings.is_important,custom_field_settings.parent,custom_field_settings.parent.name,custom_field_settings.project,custom_field_settings.project.name,custom_fields,custom_fields.date_value,custom_fields.date_value.date,custom_fields.date_value.date_time,custom_fields.display_value,custom_fields.enabled,custom_fields.enum_options,custom_fields.enum_options.color,custom_fields.enum_options.enabled,custom_fields.enum_options.name,custom_fields.enum_value,custom_fields.enum_value.color,custom_fields.enum_value.enabled,custom_fields.enum_value.name,custom_fields.id_prefix,custom_fields.input_restrictions,custom_fields.is_formula_field,custom_fields.multi_enum_values,custom_fields.multi_enum_values.color,custom_fields.multi_enum_values.enabled,custom_fields.multi_enum_values.name,custom_fields.name,custom_fields.number_value,custom_fields.representation_type,custom_fields.text_value,custom_fields.type,default_access_level,default_view,due_date,due_on,followers,followers.name,html_notes,icon,members,members.name,minimum_access_level_for_customization,minimum_access_level_for_sharing,modified_at,name,notes,owner,permalink_url,privacy_setting,project_brief,public,start_on,team,team.name,workspace,workspace.name", # list[str] | This endpoint returns a resource which excludes some properties by default. To include those optional properties, set this query parameter to a comma-separated list of the properties you wish to include.
    }

    try:
        # Get a project
        api_response = projects_api_instance.get_project(project_id, opts)        
        matches = extract_custom_fields(api_response)        
        df = pd.DataFrame(matches)
        if(printOutput):
            print(f"Calling list_project_customfields for  project id: {project_id}")   
            #print(api_response) 
            print(df)
        return df,api_response
    except Exception as e:
        print("Exception when calling ProjectsApi->list_project_customfields: %s\n" % e)





def build_client(token):
    
    # === CONFIG ===
    config = Configuration()
    config.access_token =ASANA_TOKEN
    config.verify_ssl=False

    # Handle proxy issues if needed - MiTM proxy
    #config.ssl_ca_cert = r'xxxx'
    #config.proxy = ""

    # Create API client
    api_client = ApiClient(config)
    return api_client



def list_projects(api_client,workspace_id):    

    try:       
        projects_api_instance=asana.ProjectsApi(api_client)
        opts = {'limit': 100, 'archived': False }
    
        # Get all projects in a workspace
        api_response = projects_api_instance.get_projects_for_workspace(workspace_id, opts)        
        results=[]
        for data in api_response:            
            results.append(data)
            #parents = [
            #    {
            #        "gid": item["parent"]["gid"],
            #        "name": item["parent"]["name"]
            #    }
            #    for item in data.get("custom_field_settings", []) if "parent" in item
            #]
            #print(parents)           
            #print(data.get('gid')+","+data.get('name')+","+","+str(data.get("created_by") or '')+","+str(data.get('completed') or ''))

        df = pd.DataFrame(results)
        pd.set_option("display.max_rows", None)
        print(df[["name","gid"]].sort_values(by="name").reset_index(drop=True))

    except Exception as e:
        print(f"Error listing projects: {e}")



def list_portfolios(api_client,workspace_id):
    print(f"Retrieving portfolios for workspace: {workspace_id}")
    workspaces_api_instance = asana.WorkspacesApi(api_client) 
    opts = {
        "limit": 100,
        "opt_fields": "email_domains,is_organization,name",
    }

    try:
        response = workspaces_api_instance.get_workspace(workspace_id,opts)        
        portfolios_api_instance=asana.PortfoliosApi(api_client)
       
        opts = {
        'limit': 100, # int | Results per page. The number of objects to return per page. The value must be between 1 and 100.
        'owner':"me",
        'opt_fields': "archived,color,completed,completed_at,completed_by,completed_by.name,created_at,created_from_template,created_from_template.name,current_status,current_status.author,current_status.author.name,current_status.color,current_status.created_at,current_status.created_by,current_status.created_by.name,current_status.html_text,current_status.modified_at,current_status.text,current_status.title,current_status_update,current_status_update.resource_subtype,current_status_update.title,custom_field_settings,custom_field_settings.custom_field,custom_field_settings.custom_field.asana_created_field,custom_field_settings.custom_field.created_by,custom_field_settings.custom_field.created_by.name,custom_field_settings.custom_field.currency_code,custom_field_settings.custom_field.custom_label,custom_field_settings.custom_field.custom_label_position,custom_field_settings.custom_field.date_value,custom_field_settings.custom_field.date_value.date,custom_field_settings.custom_field.date_value.date_time,custom_field_settings.custom_field.default_access_level,custom_field_settings.custom_field.description,custom_field_settings.custom_field.display_value,custom_field_settings.custom_field.enabled,custom_field_settings.custom_field.enum_options,custom_field_settings.custom_field.enum_options.color,custom_field_settings.custom_field.enum_options.enabled,custom_field_settings.custom_field.enum_options.name,custom_field_settings.custom_field.enum_value,custom_field_settings.custom_field.enum_value.color,custom_field_settings.custom_field.enum_value.enabled,custom_field_settings.custom_field.enum_value.name,custom_field_settings.custom_field.format,custom_field_settings.custom_field.has_notifications_enabled,custom_field_settings.custom_field.id_prefix,custom_field_settings.custom_field.input_restrictions,custom_field_settings.custom_field.is_formula_field,custom_field_settings.custom_field.is_global_to_workspace,custom_field_settings.custom_field.is_value_read_only,custom_field_settings.custom_field.multi_enum_values,custom_field_settings.custom_field.multi_enum_values.color,custom_field_settings.custom_field.multi_enum_values.enabled,custom_field_settings.custom_field.multi_enum_values.name,custom_field_settings.custom_field.name,custom_field_settings.custom_field.number_value,custom_field_settings.custom_field.people_value,custom_field_settings.custom_field.people_value.name,custom_field_settings.custom_field.precision,custom_field_settings.custom_field.privacy_setting,custom_field_settings.custom_field.reference_value,custom_field_settings.custom_field.reference_value.name,custom_field_settings.custom_field.representation_type,custom_field_settings.custom_field.resource_subtype,custom_field_settings.custom_field.text_value,custom_field_settings.custom_field.type,custom_field_settings.is_important,custom_field_settings.parent,custom_field_settings.parent.name,custom_field_settings.project,custom_field_settings.project.name,custom_fields,custom_fields.date_value,custom_fields.date_value.date,custom_fields.date_value.date_time,custom_fields.display_value,custom_fields.enabled,custom_fields.enum_options,custom_fields.enum_options.color,custom_fields.enum_options.enabled,custom_fields.enum_options.name,custom_fields.enum_value,custom_fields.enum_value.color,custom_fields.enum_value.enabled,custom_fields.enum_value.name,custom_fields.id_prefix,custom_fields.input_restrictions,custom_fields.is_formula_field,custom_fields.multi_enum_values,custom_fields.multi_enum_values.color,custom_fields.multi_enum_values.enabled,custom_fields.multi_enum_values.name,custom_fields.name,custom_fields.number_value,custom_fields.representation_type,custom_fields.text_value,custom_fields.type,default_access_level,default_view,due_date,due_on,followers,followers.name,html_notes,icon,members,members.name,minimum_access_level_for_customization,minimum_access_level_for_sharing,modified_at,name,notes,offset,owner,path,permalink_url,privacy_setting,project_brief,public,start_on,team,team.name,uri,workspace,workspace.name", # list[str] | This endpoint returns a resource which excludes some properties by default. To include those optional properties, set this query parameter to a comma-separated list of the properties you wish to include.
        }

    
        # Get all projects in a workspace
        api_response = portfolios_api_instance.get_portfolios(workspace_id, opts)  
        results=[]      
        for data in api_response:
            results.append(data)
            
        df = pd.DataFrame(results)
        print(df[["name","gid"]].sort_values(by="name").reset_index(drop=True))
    except Exception as e:
        print(f"Error listing workspaces: {e}")



def list_workspaces(api_client):
    workspaces_api_instance = asana.WorkspacesApi(api_client) 
    opts = {
        "limit": 100,
        "opt_fields": "email_domains,is_organization,name",
    }

    try:
        response = workspaces_api_instance.get_workspaces(opts)
        results=[]
        for ws in response:            
            results.append(ws)            
        df = pd.DataFrame(results)
        print(df)        
    except Exception as e:
        print(f"Error listing workspaces: {e}")




def main():
    parser = argparse.ArgumentParser(description="Asana automation script",
    epilog=r"""
    Examples
        python3 .\Asana_cli.py --action ls-workspaces

        python3 .\Asana_cli.py --action ls-portfolios
        python3 .\Asana_cli.py --action ls-portfolios  --workspace-id 74700000005011

        python3 .\Asana_cli.py --action ls-projects
        python3 .\Asana_cli.py --action ls-projects  --workspace-id 74700000005011

        python3 .\Asana_cli.py --action ls-project-sections
        python3 .\Asana_cli.py --action ls-project-sections --project-id 1200000000000070

        python3 .\Asana_cli.py --action ls-project-tasks 
        python3 .\Asana_cli.py --action ls-project-tasks --project-id 1200000000000070
        python3 .\Asana_cli.py --action ls-project-tasks --project-id 1200000000000070 --section-id 1200000000000072

        python3 .\Asana_cli.py --action create-project-tasks --excel .\tasks.xlsx
    """                                 
    , formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument("--token", required=False, help="Asana personal access token")
    parser.add_argument("--workspace-id", required=False, help="Asana workspace ID")
    parser.add_argument("--portofolio-id", required=False, help="Asana portofolio ID")
    parser.add_argument("--project-id", required=False, help="Asana project ID")
    parser.add_argument("--section-id", help="Asana section ID")
    parser.add_argument("--excel", help="Excel file with tasks")
    parser.add_argument("--action",required=True,choices=[
        "create-project-tasks",
        "ls-project-tasks",
        "ls-project-sections",
        "ls-project-customfields",
        "ls-projects",
        "ls-portfolios", 
        "ls-workspaces"],
        help="Action to perform",)
    args = parser.parse_args()

    
    asana_token = ASANA_TOKEN  if (pd.isna(args.token)) else args.token
    project_id= PROJECT_ID if (pd.isna(args.project_id)) else args.project_id
    section_id= SECTION_ID if (pd.isna(args.section_id)) else args.section_id
    workspace_id = WORKSPACE_ID  if (pd.isna(args.workspace_id)) else args.workspace_id

    # Build clients
    api_client = build_client(asana_token)
    users_api = UsersApi(api_client)
    sections_api = SectionsApi(api_client)
    tasks_api_instance = asana.TasksApi(api_client)    
    projects_api_instance = asana.ProjectsApi(api_client)

    if args.action == "create-project-tasks":
        if not args.excel:
            raise ValueError("Excel file is required for create action")

        df =  pd.read_excel(args.excel)
        project_sections=list_project_sections(api_client,project_id,False)
        for _, row in df.iterrows():                    
            create_project_task(projects_api_instance,tasks_api_instance,sections_api,workspace_id, project_id,row,project_sections  )

    elif args.action == "ls-workspaces":
        list_workspaces(api_client)
    elif args.action == "ls-portfolios":
        list_portfolios(api_client,workspace_id)
    elif args.action == "ls-projects":
        list_projects(api_client,workspace_id)
    elif args.action == "ls-project-sections":        
        list_project_sections(api_client,project_id)
    elif args.action == "ls-project-tasks":  
        custom_fields=["Discovery","Severity","Domain"]      
        section_id= None if (pd.isna(args.section_id)) else args.section_id
        list_tasks_in_project(api_client,project_id,custom_fields,section_id)
    elif args.action == "ls-project-customfields":        
        list_project_customfields(projects_api_instance,project_id)

        

    


if __name__ == "__main__":
    main()


