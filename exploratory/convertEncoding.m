% convertEncoding.m
%----------------------------------------------------------------------
%CONVERTENCODING Change the character encoding of a file
% CONVERTENCODING(FILENAME, CURRENTENCODING, NEWENCODING) converts the
% file FILENAME from character encoding CURRENTENCODING to a new
% encoding specified by NEWENCODING. A copy of the original version of
% FILENAME is placed at FILENAME.old.
%
% INPUT PARAMETERS:
% FILENAME: The name of the file to be converted.
% CURRENTENCODING: The encoding currently be used by FILENAME.
% NEWENCODING: The encoding to rewrite FILENAME in.
function convertEncoding(filename, currentEncoding, newEncoding)

bakFile = [filename, '.old'];
movefile(filename, bakFile);

fpIn = fopen(bakFile, 'r', 'n', currentEncoding);
fpOut = fopen(filename, 'w', 'n', newEncoding);

while feof(fpIn) == 0
    lineIn = fgets(fpIn);
    fwrite(fpOut, lineIn, 'char');
end

fclose(fpIn);
fclose(fpOut);

end
%----------------------------------------------------------------------