function indices = xview_classes2indices(classes)
% remap xview classes 11-94 to 0-61
indices = [ 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1.0, 2.0, 0, 3.0, 0, 4.0, 5.0, 6.0, 7.0, 8.0, 0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 0, 0, 16.0, 17.0, 18.0, 19.0, 20.0, 21.0, 22.0, 0, 23.0, 24.0, 25.0, 0, 26.0, 27.0, 0, 28.0, 0, 29.0, 30.0, 31.0, 32.0, 33.0, 34.0, 35.0, 36.0, 37.0, 0, 38.0, 39.0, 40.0, 41.0, 42.0, 43.0, 44.0, 45.0, 0, 0, 0, 0, 46.0, 47.0, 48.0, 49.0, 0, 50.0, 51.0, 0, 52.0, 0, 0, 0, 53.0, 54.0, 0, 55.0, 0, 0, 56.0, 0, 57.0, 0, 58.0, 59.0];
indices = indices(classes);    
end   