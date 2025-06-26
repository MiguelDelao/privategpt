#!/bin/bash
# Prompt Management Helper Script

# Configuration
BASE_URL="${BASE_URL:-http://localhost:8000}"
TOKEN="${JWT_TOKEN:-}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if token is set
if [ -z "$TOKEN" ]; then
    echo -e "${RED}Error: JWT_TOKEN environment variable not set${NC}"
    echo "Usage: JWT_TOKEN=your_token ./manage_prompts.sh"
    exit 1
fi

# Function to list all prompts
list_prompts() {
    echo -e "${BLUE}Listing all prompts...${NC}"
    curl -s -H "Authorization: Bearer $TOKEN" \
        "$BASE_URL/api/prompts/" | jq '.'
}

# Function to get a specific prompt
get_prompt() {
    local prompt_id=$1
    echo -e "${BLUE}Getting prompt $prompt_id...${NC}"
    curl -s -H "Authorization: Bearer $TOKEN" \
        "$BASE_URL/api/prompts/$prompt_id" | jq '.'
}

# Function to create a new prompt
create_prompt() {
    local name=$1
    local pattern=$2
    local xml_file=$3
    
    if [ ! -f "$xml_file" ]; then
        echo -e "${RED}Error: XML file not found: $xml_file${NC}"
        return 1
    fi
    
    # Read and escape XML content
    local xml_content=$(cat "$xml_file" | jq -Rs .)
    
    echo -e "${BLUE}Creating prompt '$name' with pattern '$pattern'...${NC}"
    
    curl -s -X POST \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        "$BASE_URL/api/prompts/" \
        -d "{
            \"name\": \"$name\",
            \"model_pattern\": \"$pattern\",
            \"prompt_xml\": $xml_content,
            \"description\": \"Created via manage_prompts.sh\",
            \"is_default\": false
        }" | jq '.'
}

# Function to update a prompt
update_prompt() {
    local prompt_id=$1
    local xml_file=$2
    
    if [ ! -f "$xml_file" ]; then
        echo -e "${RED}Error: XML file not found: $xml_file${NC}"
        return 1
    fi
    
    local xml_content=$(cat "$xml_file" | jq -Rs .)
    
    echo -e "${BLUE}Updating prompt $prompt_id...${NC}"
    
    curl -s -X PATCH \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        "$BASE_URL/api/prompts/$prompt_id" \
        -d "{\"prompt_xml\": $xml_content}" | jq '.'
}

# Function to test a prompt
test_prompt() {
    local xml_file=$1
    local model=${2:-"qwen2.5:3b"}
    local message=${3:-"Hello, please introduce yourself and explain what tools you have access to."}
    
    if [ ! -f "$xml_file" ]; then
        echo -e "${RED}Error: XML file not found: $xml_file${NC}"
        return 1
    fi
    
    local xml_content=$(cat "$xml_file" | jq -Rs .)
    
    echo -e "${BLUE}Testing prompt with model $model...${NC}"
    echo -e "${YELLOW}Test message: $message${NC}"
    
    curl -s -X POST \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        "$BASE_URL/api/prompts/test" \
        -d "{
            \"prompt_xml\": $xml_content,
            \"model_name\": \"$model\",
            \"test_message\": \"$message\"
        }" | jq '.'
}

# Function to delete a prompt
delete_prompt() {
    local prompt_id=$1
    echo -e "${YELLOW}Are you sure you want to delete prompt $prompt_id? (y/N)${NC}"
    read -r confirm
    
    if [[ $confirm == [yY] ]]; then
        echo -e "${BLUE}Deleting prompt $prompt_id...${NC}"
        curl -s -X DELETE \
            -H "Authorization: Bearer $TOKEN" \
            "$BASE_URL/api/prompts/$prompt_id"
        echo -e "${GREEN}Prompt deleted${NC}"
    else
        echo "Cancelled"
    fi
}

# Function to export all prompts
export_prompts() {
    local export_dir=${1:-"./prompt_exports"}
    mkdir -p "$export_dir"
    
    echo -e "${BLUE}Exporting all prompts to $export_dir...${NC}"
    
    # Get all prompts
    local prompts=$(curl -s -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/prompts/")
    
    # Export each prompt
    echo "$prompts" | jq -c '.[]' | while read -r prompt; do
        local name=$(echo "$prompt" | jq -r '.name')
        local id=$(echo "$prompt" | jq -r '.id')
        local xml=$(echo "$prompt" | jq -r '.prompt_xml')
        
        # Save prompt XML
        echo "$xml" > "$export_dir/${name}_${id}.xml"
        
        # Save prompt metadata
        echo "$prompt" | jq '.' > "$export_dir/${name}_${id}.json"
        
        echo -e "${GREEN}Exported: ${name}_${id}${NC}"
    done
    
    echo -e "${GREEN}All prompts exported to $export_dir${NC}"
}

# Function to show prompt for specific model
get_model_prompt() {
    local model=$1
    echo -e "${BLUE}Getting prompt for model: $model${NC}"
    curl -s -H "Authorization: Bearer $TOKEN" \
        "$BASE_URL/api/prompts/for-model/$model" | jq '.'
}

# Create sample prompt files
create_samples() {
    echo -e "${BLUE}Creating sample prompt files...${NC}"
    
    # Basic MCP prompt
    cat > mcp_basic.xml << 'EOF'
<system>
<persona>
You are PrivateGPT with document search capabilities through MCP tools.
</persona>

<tools>
You have access to:
- search_documents(query, limit): Search uploaded documents
- rag_chat(question): Get comprehensive answers from documents
</tools>

<rules>
- Always search before answering document questions
- Be transparent about what you're searching for
- Cite sources when providing information
</rules>
</system>
EOF

    # Advanced MCP prompt
    cat > mcp_advanced.xml << 'EOF'
<system>
<identity>PrivateGPT - Local AI Assistant with Advanced Capabilities</identity>

<capabilities>
<document_tools>
- search_documents: Semantic search through uploaded content
- rag_chat: Context-aware answers with citations
</document_tools>

<file_tools>
- read_file: Read local files
- create_file: Create new files
- edit_file: Modify existing files
- list_directory: Browse folders
</file_tools>

<system_tools>
- get_system_info: Hardware and software information
- check_service_health: Service status monitoring
</system_tools>
</capabilities>

<communication_style>
- Professional yet friendly
- Always explain tool usage
- Show thinking process in <thinking> tags
- Use <status> for progress updates
- Use <error> for error messages
</communication_style>

<tool_usage_rules priority="critical">
1. MANDATORY: Use search_documents before answering ANY question about documents
2. Show search queries transparently: [Searching: "your query"]
3. If search returns no results, say so explicitly
4. Never fabricate document content
5. Chain tools when necessary (search → read_file for details)
</tool_usage_rules>

<output_format>
<thinking>Internal reasoning about approach</thinking>
[Tool usage shown in brackets]
Clear, structured response to user
</output_format>
</system>
EOF

    echo -e "${GREEN}Created mcp_basic.xml and mcp_advanced.xml${NC}"
}

# Main menu
show_menu() {
    echo -e "\n${BLUE}=== Prompt Management Tool ===${NC}"
    echo "1. List all prompts"
    echo "2. Get specific prompt"
    echo "3. Create new prompt"
    echo "4. Update existing prompt"
    echo "5. Test a prompt"
    echo "6. Delete a prompt"
    echo "7. Export all prompts"
    echo "8. Get prompt for model"
    echo "9. Create sample prompt files"
    echo "0. Exit"
    echo -e "${YELLOW}Select an option:${NC}"
}

# Main loop
if [ $# -eq 0 ]; then
    # Interactive mode
    while true; do
        show_menu
        read -r choice
        
        case $choice in
            1)
                list_prompts
                ;;
            2)
                echo "Enter prompt ID:"
                read -r prompt_id
                get_prompt "$prompt_id"
                ;;
            3)
                echo "Enter prompt name:"
                read -r name
                echo "Enter model pattern (e.g., 'privategpt-mcp', '*mcp*'):"
                read -r pattern
                echo "Enter XML file path:"
                read -r xml_file
                create_prompt "$name" "$pattern" "$xml_file"
                ;;
            4)
                echo "Enter prompt ID to update:"
                read -r prompt_id
                echo "Enter XML file path:"
                read -r xml_file
                update_prompt "$prompt_id" "$xml_file"
                ;;
            5)
                echo "Enter XML file path:"
                read -r xml_file
                echo "Enter model name (default: qwen2.5:3b):"
                read -r model
                echo "Enter test message:"
                read -r message
                test_prompt "$xml_file" "${model:-qwen2.5:3b}" "$message"
                ;;
            6)
                echo "Enter prompt ID to delete:"
                read -r prompt_id
                delete_prompt "$prompt_id"
                ;;
            7)
                echo "Enter export directory (default: ./prompt_exports):"
                read -r export_dir
                export_prompts "${export_dir:-./prompt_exports}"
                ;;
            8)
                echo "Enter model name:"
                read -r model
                get_model_prompt "$model"
                ;;
            9)
                create_samples
                ;;
            0)
                echo "Goodbye!"
                exit 0
                ;;
            *)
                echo -e "${RED}Invalid option${NC}"
                ;;
        esac
    done
else
    # Command line mode
    case $1 in
        list)
            list_prompts
            ;;
        get)
            get_prompt "$2"
            ;;
        create)
            create_prompt "$2" "$3" "$4"
            ;;
        update)
            update_prompt "$2" "$3"
            ;;
        test)
            test_prompt "$2" "$3" "$4"
            ;;
        delete)
            delete_prompt "$2"
            ;;
        export)
            export_prompts "$2"
            ;;
        model)
            get_model_prompt "$2"
            ;;
        samples)
            create_samples
            ;;
        *)
            echo "Usage: $0 [list|get|create|update|test|delete|export|model|samples] [args...]"
            echo "Or run without arguments for interactive mode"
            exit 1
            ;;
    esac
fi