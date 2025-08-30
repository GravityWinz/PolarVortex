# File uploading process
## General Archetecture
    The following directory structure will be used:
local_storage/
├── images/
│   ├── <image_name>               # A directory for each new image, it will use the name of the origional image file
│   |   ├── image_name.<ext>       # The origional image file which was updated
│   |   ├── thumb_image_name.png   # thumbnail image
│   |    └── ...                    # other post processed versions of that image - TBD
│   ├── <next image name>          # Next image and 
│   |    ├── image_name.<ext>       # The origional image file which was updated
│   |    ├── thumb_image_name.png   # thumbnail image
│   |    └── ...                    # other post processed versions of that image - TBD

## Flow for the file upload process
1) User will be presented a file picker to chose the file 
2) will then select upload. 
3) image data and file name will be passed to back end
4) New directory for image will be created under local_storage/images using the images name as the directory
5) The origional image will be stored in this directory


## update 1
Add an additional text box on the upload page to allow setting the name of the directory created under images, this will override the images file's name for the assets stored there
By default populated that fields with the selected images name
If there is a name collision indicate that and force the user to put in a different name prior to upload