#!/bin/bash
DIR=`dirname $0`
LPCPUDIR=$1
CHART_TYPE=$2
if [ -z "${LPCPUDIR}" ]; then echo "ERROR: You must specify where the LPCPU package is installed"; exit 1; fi
if [ -n "${CHART_TYPE}" -a "${CHART_TYPE}" == "chart.pl" ]; then echo "Forcing the use of chart.pl instead of jschart"; export FORCE_CHART_PL=1; fi
LPCPUDIR=`readlink -e ${LPCPUDIR}`
ARCH=`uname -m | sed -e "s/i.86/i386/"`
CHART_DIRECTOR=""
if [ "${FORCE_CHART_PL}" == "1" ]; then if [ "${ARCH}" == "i386" ]; then CHART_DIRECTOR="${LPCPUDIR}/tools/chart-lib.32bit"; elif [ "${ARCH}" == "x86_64" ]; then CHART_DIRECTOR="${LPCPUDIR}/tools/chart-lib.64bit"; else echo "Forcing usage of chart.pl requires a 32bit or 64bit x86 platform"; fi; fi
export PERL5LIB=${LPCPUDIR}/perl
if [ ! -e "${LPCPUDIR}/tools/jschart.pm/d3.min.js" -o ! -e "${LPCPUDIR}/tools/jschart.pm/queue.min.js" ]; then export FORCE_JSCHART_REMOTE_LIBRARY=1; fi
# avoid some issues with postprocessing scripts requiring large number of file handles, only works if postprocess.sh is executed as root
ulimit -n 500000
pushd $DIR > /dev/null
# make sure all chart.sh scripts are deleted in case we are doing a repostprocess with a different chart implementation than before
find . -name chart.sh -execdir rm "{}" \;

${LPCPUDIR}/postprocess/postprocess-sar . 001 default

${LPCPUDIR}/postprocess/postprocess-iostat --dir=. --run-number=001 --id=default --bdh=block-device-hierarchy.dat

if [ -f ./system-topology.dump ]; then
${LPCPUDIR}/postprocess/postprocess-mpstat .  001 default ./system-topology.dump
else
MPSTAT_NO_NUMA=1 ${LPCPUDIR}/postprocess/postprocess-mpstat . 001 default
fi

${LPCPUDIR}/postprocess/postprocess-vmstat . 001 default



${LPCPUDIR}/postprocess/postprocess-meminfo-watch . 001 default

if [ -f ./system-topology.dump ]; then
${LPCPUDIR}/postprocess/postprocess-proc-interrupts . 001 default ./system-topology.dump
else
PROC_INTERRUPTS_NO_NUMA=1 ${LPCPUDIR}/postprocess/postprocess-proc-interrupts . 001 default
fi





link_files="top.default.001 "
# make sure summary.html is deleted in case we are doing a repostprocess
rm summary.html > /dev/null 2>&1
if [ "${FORCE_CHART_PL}" == "1" ]; then if [ ! -z "${CHART_DIRECTOR}" ]; then ${LPCPUDIR}/tools/chart-processor.sh chart=${LPCPUDIR}/tools/chart.pl chart_lib=${CHART_DIRECTOR} link_files="${link_files}"; else echo "Skipping chart-processor.sh execution due to no valid chart.pl libraries"; fi; else ${LPCPUDIR}/tools/chart-processor.sh chart= chart_lib= link_files="${link_files}"; fi

NDIFF="${LPCPUDIR}/tools/ndiff.py"
if [ -x ${NDIFF} -a -e interrupts.before -a -e interrupts.after ]; then ${NDIFF} interrupts.before interrupts.after > interrupts.diff; fi
if [ -x ${NDIFF} -a -e netstat.before -a -e netstat.after ]; then ${NDIFF} netstat.before netstat.after > netstat.diff; fi
if [ -x ${NDIFF} -a -e netstat-in.before -a -e netstat-in.after ]; then ${NDIFF} netstat-in.before netstat-in.after > netstat-in.diff; fi
if [ -e netstat-v.before -a -e netstat-v.after ]; then diff netstat-v.before netstat-v.after > netstat-v.diff; fi
if [ -x ${NDIFF} -a -e netstat-s.before -a -e netstat-s.after ]; then ${NDIFF} netstat-s.before netstat-s.after > netstat-s.diff; fi
if [ -x ${NDIFF} -a -e meminfo.before -a -e meminfo.after ]; then ${NDIFF} meminfo.before meminfo.after > meminfo.diff; fi
if [ -x ${NDIFF} -a -e df.before -a -e df.after ]; then ${NDIFF} df.before df.after > df.diff; fi
if [ -x ${NDIFF} -a -e ip-statistics.before -a -e ip-statistics.after ]; then ${NDIFF} ip-statistics.before ip-statistics.after > ip-statistics.diff; fi
if [ -x ${NDIFF} -a -e ifconfig.before -a -e ifconfig.after ]; then ${NDIFF} ifconfig.before ifconfig.after > ifconfig.diff; fi
if [ -x ${NDIFF} -a -e snmp.before -a -e snmp.after ]; then ${NDIFF} snmp.before snmp.after > snmp.diff; fi
if [ -x ${NDIFF} -a -e ethtool/ethtool-eth0-stats.before.STDOUT -a -e ethtool/ethtool-eth0-stats.after.STDOUT  ]; then ${NDIFF} ethtool/ethtool-eth0-stats.before.STDOUT ethtool/ethtool-eth0-stats.after.STDOUT > ethtool/ethtool-eth0-stats.diff ; fi
