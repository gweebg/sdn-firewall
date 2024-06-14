registers=(
#   "MyEgress.bloom_filter_state"
#   "MyEgress.bloom_filter_privatePort"
#   "MyEgress.bloom_filter_privateAddr"
#   "MyEgress.bloom_filter_publicPort"
#   "MyEgress.bloom_filter_publicAddr"
    "MyEgress.fiveT_localPort"
    "MyEgress.fiveT_remotePort"
    "MyEgress.fiveT_localAddr"
    "MyEgress.fiveT_remoteAddr"
    "MyEgress.entryTS"
    "MyEgress.direction"
    "MyEgress.newState"
    "MyEgress.read_state"
    "MyEgress.read_privatePort"
    "MyEgress.read_privateAddr"
    "MyEgress.read_publicPort"
    "MyEgress.read_publicAddr"
)

for register in "${registers[@]}"; do
  echo "register_read $register" | simple_switch_CLI --thrift-port 9093 | grep , | sed -e 's/.*= //' | sed -e 's/, \?/\n/g' > "dbug/$register"
done