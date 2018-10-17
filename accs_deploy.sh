#!/bin/bash

PSM_URL="https://psm.us.oraclecloud.com"

function prepare_storage()
{
curl \
	-u "${USERNAME}:${PASSWORD}" \
	"${STORAGE_URL}"

curl \
	-X PUT \
	-u "${USERNAME}:${PASSWORD}" \
	"${STORAGE_URL}/${APPLICATION}"

curl \
	-X PUT \
	-u "${USERNAME}:${PASSWORD}" \
	"${STORAGE_URL}/${APPLICATION}/${APPLICATION_ARCHIVE_NAME}" \
	-T ${APPLICATION_ARCHIVE}

curl \
	-u "${USERNAME}:${PASSWORD}" \
	"${STORAGE_URL}/${APPLICATION}"
}

function deploy_app()
{
curl \
	-i \
	-X POST \
	-u "${USERNAME}:${PASSWORD}" \
	-H "X-ID-TENANT-NAME:${IDENTITY_DOMAIN}" \
	-H "Content-Type: multipart/form-data" \
	-F "name=${APPLICATION}" \
	-F "runtime=java" \
	-F "subscription=Hourly" \
	-F "archiveURL=${APPLICATION}/${APPLICATION_ARCHIVE_NAME}" \
	"${PSM_URL}/paas/service/apaas/api/v1.1/apps/${IDENTITY_DOMAIN}"

curl \
	-i \
	-u "${USERNAME}:${PASSWORD}" \
	-H "X-ID-TENANT-NAME:${IDENTITY_DOMAIN}" \
    "${PSM_URL}/paas/service/apaas/api/v1.1/apps/${IDENTITY_DOMAIN}/${APPLICATION}"
}

if [ -z "${USERNAME}" ] ; then
    echo "Required environment USERNAME not set"
    exit 1
fi

if [ -z "${PASSWORD}" ] ; then
    echo "Required environment PASSWORD not set"
    exit 1
fi

if [ -z "${IDENTITY_DOMAIN}" ] ; then
    echo "Required environment IDENTITY_DOMAIN not set"
    exit 1
fi

if [ -z "${STORAGE_URL}" ] ; then
    echo "Required environment STORAGE_URL not set"
    exit 1
fi

if [ $# -ne 3 ] ; then
    echo "usage: $0 app_name app_version archive_file"
    exit 1
fi

APPLICATION="${1}"
APPLICATION_VERSION="${2}"
APPLICATION_ARCHIVE="${3}"

APPLICATION_ARCHIVE_BASENAME=$(basename ${APPLICATION_ARCHIVE})
APPLICATION_ARCHIVE_PREFIX=${APPLICATION_ARCHIVE_BASENAME%%.*}
APPLICATION_ARCHIVE_SUFFIX=${APPLICATION_ARCHIVE_BASENAME#*.}
APPLICATION_ARCHIVE_NAME="${APPLICATION_ARCHIVE_PREFIX}-${APPLICATION_VERSION}.${APPLICATION_ARCHIVE_SUFFIX}"


if [ ! -f "${APPLICATION_ARCHIVE}" ] ; then
    echo "Application archive file ${APPLICATION_ARCHIVE} does not exist"
    exit 1
fi

prepare_storage
deploy_app
