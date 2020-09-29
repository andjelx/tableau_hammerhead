#!/bin/bash -ex

download() {
  echo "downloading from $1 to $2"
  aws s3 cp $1 ./ --no-progress
}

download_recursive() {
  echo "downloading recursively from $1 to $2"
  aws s3 cp $1 $2 --no-progress --recursive
}

upload() {
  echo "uploading from $1 to $2"
  aws s3 cp $1 $2 --acl bucket-owner-full-control --no-progress
}

upload_recursive() {
  echo "uploading recursively from $1 to $2"
  aws s3 cp $1 $2 --acl bucket-owner-full-control --no-progress --recursive
}
