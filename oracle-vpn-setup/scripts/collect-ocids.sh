#!/usr/bin/env bash
# collect-ocids.sh — print the OCIDs oracle-grab.sh needs, for one ~/.oci/config profile.
# Usage: bash collect-ocids.sh [PROFILE]     (default: DEFAULT)
# Output: export lines you can paste / eval. Read-only.
set -euo pipefail
PROFILE="${1:-DEFAULT}"
O=(--profile "$PROFILE")

TENANCY=$(awk -v p="[$PROFILE]" '$0==p{f=1;next} /^\[/{f=0} f&&/^tenancy=/{sub(/^tenancy=/,"");print;exit}' ~/.oci/config)
REGION=$(awk -v p="[$PROFILE]" '$0==p{f=1;next} /^\[/{f=0} f&&/^region=/{sub(/^region=/,"");print;exit}' ~/.oci/config)
[[ -n "$TENANCY" ]] || { echo "profile $PROFILE not found in ~/.oci/config" >&2; exit 1; }

echo "# profile=$PROFILE region=$REGION"
echo "export PROFILE=$PROFILE"
echo "export COMPARTMENT=$TENANCY"

ADS=$(oci iam availability-domain list --compartment-id "$TENANCY" "${O[@]}" --query 'data[].name' --raw-output | tr -d '[]", ' | grep -v '^$' | tr '\n' ' ')
echo "export ADS=\"${ADS% }\""

echo "# subnets (public one has prohibitPublicIp=False):"
oci network subnet list --compartment-id "$TENANCY" "${O[@]}" \
  --query 'data[].{name:"display-name",id:id,prohibitPublicIp:"prohibit-public-ip-on-vnic"}' --output table || true
SUBNET=$(oci network subnet list --compartment-id "$TENANCY" "${O[@]}" \
  --query 'data[?"prohibit-public-ip-on-vnic"==`false`] | [0].id' --raw-output 2>/dev/null || true)
echo "export SUBNET=${SUBNET}"

for shape in VM.Standard.A1.Flex VM.Standard.E2.1.Micro; do
  IMG=$(oci compute image list --compartment-id "$TENANCY" "${O[@]}" \
    --operating-system "Canonical Ubuntu" --operating-system-version "22.04" --shape "$shape" \
    --sort-by TIMECREATED --sort-order DESC --query 'data[0].id' --raw-output 2>/dev/null || true)
  var=IMAGE_A1; [[ $shape == *E2* ]] && var=IMAGE_E2
  echo "export ${var}=${IMG}"
done

echo "# A1 limits:"
oci limits value list --compartment-id "$TENANCY" "${O[@]}" --service-name compute --all \
  --query "data[?contains(name,'standard-a1-core-count') || contains(name,'standard-a1-memory-count')].{name:name,value:value,ad:\"availability-domain\"}" --output table 2>/dev/null || true
