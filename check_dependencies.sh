#!/bin/bash

#
# LPCPU Dependency Checker
# Checks for required and optional packages needed by lpcpu.sh
# Provides installation suggestions for missing packages
#

echo "=========================================="
echo "LPCPU Dependency Checker"
echo "=========================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track missing packages
MISSING_PACKAGES=()
MISSING_CRITICAL=()

# Detect package manager
detect_package_manager() {
    if command -v zypper &> /dev/null; then
        echo "sles"
    elif command -v yum &> /dev/null; then
        echo "rhel"
    elif command -v apt-get &> /dev/null; then
        echo "debian"
    else
        echo "unknown"
    fi
}

PKG_MANAGER=$(detect_package_manager)

# Function to check if a command exists
check_command() {
    local cmd=$1
    local package=$2
    local critical=$3
    local description=$4
    
    if command -v "$cmd" &> /dev/null; then
        echo -e "${GREEN}✓${NC} $cmd - installed ($description)"
        return 0
    else
        if [ "$critical" = "yes" ]; then
            echo -e "${RED}✗${NC} $cmd - MISSING ($description)"
            MISSING_CRITICAL+=("$package")
        else
            echo -e "${YELLOW}○${NC} $cmd - missing ($description)"
        fi
        MISSING_PACKAGES+=("$package")
        return 1
    fi
}

echo "Checking core system profiling tools..."
echo "----------------------------------------"

# Core profiling tools (from sysstat package)
check_command "sar" "sysstat" "yes" "System Activity Reporter"
check_command "iostat" "sysstat" "yes" "I/O statistics"
check_command "mpstat" "sysstat" "yes" "Processor statistics"

# System monitoring tools
check_command "vmstat" "procps" "yes" "Virtual memory statistics"
check_command "top" "procps" "yes" "Process monitor"
check_command "ps" "procps" "yes" "Process status"
check_command "free" "procps" "yes" "Memory usage"

echo ""
echo "Checking network tools..."
echo "----------------------------------------"

# Network tools - Check for modern (iproute2) vs legacy (net-tools)
HAS_NETSTAT=false
HAS_IPROUTE2_TOOLS=false

# Check for netstat (legacy)
if check_command "netstat" "net-tools" "no" "Network statistics (legacy)"; then
    HAS_NETSTAT=true
fi

# Check for iproute2 tools (modern replacements)
IPROUTE2_COUNT=0
if check_command "ss" "iproute2" "no" "Socket statistics (modern netstat replacement)"; then
    ((IPROUTE2_COUNT++))
    HAS_IPROUTE2_TOOLS=true
fi

if check_command "ip" "iproute2" "no" "IP configuration and statistics"; then
    ((IPROUTE2_COUNT++))
    HAS_IPROUTE2_TOOLS=true
fi

if check_command "nstat" "iproute2" "no" "Network statistics"; then
    ((IPROUTE2_COUNT++))
fi

# Check ifconfig (legacy, but still used by lpcpu)
check_command "ifconfig" "net-tools" "no" "Network interface configuration (legacy)"

# Evaluate network tools situation
echo ""
if [ "$HAS_NETSTAT" = false ] && [ "$HAS_IPROUTE2_TOOLS" = false ]; then
    echo -e "${RED}WARNING: No network statistics tools found!${NC}"
    echo "  lpcpu.sh uses netstat for network data collection."
    echo "  Neither netstat (legacy) nor iproute2 tools (modern) are installed."
    MISSING_CRITICAL+=("net-tools OR iproute2")
elif [ "$HAS_NETSTAT" = false ]; then
    echo -e "${YELLOW}NOTE: netstat not found, but iproute2 tools are available.${NC}"
    echo "  Consider modifying lpcpu.sh to use 'ss' instead of 'netstat'."
fi

echo ""
echo "Checking optional profiling tools..."
echo "----------------------------------------"

# Optional but useful tools
check_command "perf" "perf" "no" "Performance analysis tool"
check_command "oprofile" "oprofile" "no" "System-wide profiler"
check_command "tcpdump" "tcpdump" "no" "Network packet analyzer"
check_command "lsof" "lsof" "no" "List open files"
check_command "iotop" "iotop" "no" "I/O monitor"
check_command "slabtop" "procps" "no" "Kernel slab cache monitor"
check_command "cpupower" "cpupower" "no" "CPU frequency utilities"

echo ""
echo "Checking system information tools..."
echo "----------------------------------------"

check_command "lscpu" "util-linux" "no" "CPU information"
check_command "lspci" "pciutils" "no" "PCI device information"
check_command "lsscsi" "lsscsi" "no" "SCSI device information"
check_command "lsblk" "util-linux" "no" "Block device information"
check_command "lsmod" "kmod" "no" "Kernel module information"
check_command "uname" "coreutils" "no" "System information"
check_command "df" "coreutils" "no" "Disk space usage"

echo ""
echo "=========================================="
echo "Summary"
echo "=========================================="

if [ ${#MISSING_CRITICAL[@]} -eq 0 ]; then
    echo -e "${GREEN}✓ All critical tools are installed!${NC}"
else
    echo -e "${RED}✗ Missing critical tools: ${#MISSING_CRITICAL[@]}${NC}"
fi

if [ ${#MISSING_PACKAGES[@]} -eq 0 ]; then
    echo -e "${GREEN}✓ All tools are installed!${NC}"
    exit 0
fi

echo ""
echo "Missing packages: ${#MISSING_PACKAGES[@]}"
echo ""

# Generate installation recommendations
echo "=========================================="
echo "Installation Recommendations"
echo "=========================================="
echo ""

# Deduplicate package list
UNIQUE_PACKAGES=($(echo "${MISSING_PACKAGES[@]}" | tr ' ' '\n' | sort -u | tr '\n' ' '))

case "$PKG_MANAGER" in
    sles)
        echo "For SUSE Linux Enterprise Server (SLES), run:"
        echo ""
        echo "  sudo zypper install -y ${UNIQUE_PACKAGES[@]}"
        echo ""
        
        # Special recommendation for network tools
        if [ "$HAS_NETSTAT" = false ] && [ "$HAS_IPROUTE2_TOOLS" = false ]; then
            echo -e "${YELLOW}IMPORTANT: Install network tools${NC}"
            echo "  Option 1 (Recommended - Modern): sudo zypper install -y iproute2"
            echo "  Option 2 (Legacy - Used by lpcpu): sudo zypper install -y net-tools"
            echo "  Option 3 (Both): sudo zypper install -y iproute2 net-tools"
            echo ""
        elif [ "$HAS_NETSTAT" = false ]; then
            echo -e "${YELLOW}RECOMMENDED: Install netstat for lpcpu compatibility${NC}"
            echo "  sudo zypper install -y net-tools"
            echo ""
        fi
        ;;
        
    rhel)
        echo "For Red Hat Enterprise Linux / CentOS / Fedora, run:"
        echo ""
        echo "  sudo yum install -y ${UNIQUE_PACKAGES[@]}"
        echo ""
        
        if [ "$HAS_NETSTAT" = false ] && [ "$HAS_IPROUTE2_TOOLS" = false ]; then
            echo -e "${YELLOW}IMPORTANT: Install network tools${NC}"
            echo "  Option 1 (Recommended - Modern): sudo yum install -y iproute"
            echo "  Option 2 (Legacy - Used by lpcpu): sudo yum install -y net-tools"
            echo "  Option 3 (Both): sudo yum install -y iproute net-tools"
            echo ""
        elif [ "$HAS_NETSTAT" = false ]; then
            echo -e "${YELLOW}RECOMMENDED: Install netstat for lpcpu compatibility${NC}"
            echo "  sudo yum install -y net-tools"
            echo ""
        fi
        ;;
        
    debian)
        echo "For Debian / Ubuntu, run:"
        echo ""
        echo "  sudo apt-get update"
        echo "  sudo apt-get install -y ${UNIQUE_PACKAGES[@]}"
        echo ""
        
        if [ "$HAS_NETSTAT" = false ] && [ "$HAS_IPROUTE2_TOOLS" = false ]; then
            echo -e "${YELLOW}IMPORTANT: Install network tools${NC}"
            echo "  Option 1 (Recommended - Modern): sudo apt-get install -y iproute2"
            echo "  Option 2 (Legacy - Used by lpcpu): sudo apt-get install -y net-tools"
            echo "  Option 3 (Both): sudo apt-get install -y iproute2 net-tools"
            echo ""
        elif [ "$HAS_NETSTAT" = false ]; then
            echo -e "${YELLOW}RECOMMENDED: Install netstat for lpcpu compatibility${NC}"
            echo "  sudo apt-get install -y net-tools"
            echo ""
        fi
        ;;
        
    *)
        echo "Unknown package manager. Please install these packages manually:"
        echo ""
        for pkg in "${UNIQUE_PACKAGES[@]}"; do
            echo "  - $pkg"
        done
        echo ""
        
        if [ "$HAS_NETSTAT" = false ] && [ "$HAS_IPROUTE2_TOOLS" = false ]; then
            echo -e "${YELLOW}IMPORTANT: Install network tools${NC}"
            echo "  You need either 'net-tools' (for netstat) or 'iproute2' (for ss, ip, nstat)"
            echo ""
        fi
        ;;
esac

# Special note about network tools
if [ "$HAS_NETSTAT" = false ] && [ "$IPROUTE2_COUNT" -gt 0 ] && [ "$IPROUTE2_COUNT" -lt 3 ]; then
    echo -e "${YELLOW}NOTE: Partial iproute2 installation detected${NC}"
    echo "  You have some iproute2 tools but not all. Consider installing the full package."
    echo ""
fi

echo "=========================================="
echo "Additional Notes"
echo "=========================================="
echo ""
echo "• lpcpu.sh currently uses 'netstat' for network statistics"
echo "• Modern systems use 'ss' (from iproute2) as a replacement for netstat"
echo "• If netstat is missing, consider modifying lpcpu.sh to use 'ss' instead"
echo "• All network data is also available in /proc/net/* files"
echo ""

if [ ${#MISSING_CRITICAL[@]} -gt 0 ]; then
    echo -e "${RED}⚠ Critical tools are missing. lpcpu.sh may fail to run.${NC}"
    exit 1
else
    echo -e "${GREEN}✓ All critical tools are present. lpcpu.sh should run successfully.${NC}"
    if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
        echo -e "${YELLOW}  (Some optional tools are missing but not required)${NC}"
    fi
    exit 0
fi

# Made with Bob
