import os
root=os.path.dirname(__import__('mediapipe').__file__)
for dirpath,dirs,files in os.walk(root):
    for f in files:
        if f.endswith('.tflite') or f.endswith('.task'):
            print(os.path.join(dirpath,f))
print('SEARCH_DONE')
