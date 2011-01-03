#!/usr/bin/perl

my ($zip , $movie , $delay , $colX , $colY , $colZ , $vecX , $vecY , $vecZ , $energy_col , $energy_cut) = @ARGV ;
=head
my $zip = "Checkpoints.zip" ;
my $movie = "Movie.gif" ;
my $delay = 10 ;
my $colX = 4 ;
my $colY = 5 ;
my $vecX = $colX + 3 ;
my $vecY = $colY + 3 ;
my $energy_col = 10 ;
my $energy_cut = -2 ;
=cut
print "Args = " . join( " " , @ARGV ) ;
`unzip $zip` ;

chomp( my $dir = `dirname $0` ) ;
if ($dir eq '' ) { $dir = '.' ; }
`cp $dir/gnuplot /tmp/$$.gnuplot` ;
`chmod 755 /tmp/$$.gnuplot` ;


chomp( my $Xmax = `cat *.chkpt | awk '{print\$$colX}' | sort -r -n | head -1` ) ;
chomp( my $Ymax = `cat *.chkpt | awk '{print\$$colY}' | sort -r -n | head -1` ) ;
chomp( my $Xmin = `cat *.chkpt | awk '{print\$$colX}' | sort -n | head -1` ) ;
chomp( my $Ymin = `cat *.chkpt | awk '{print\$$colY}' | sort -n | head -1` ) ;

$Xmax += 1 ;
$Xmin -= 1 ;
$Ymax += 1 ;
$Ymin -= 1 ;
chomp( my @files = `ls -1 *.chkpt` ) ;
foreach my $file ( @files )
{
	my $png_file = "$file.png" ;
	my $out_file = "$file.filt" ; 
	&filter( $file , $out_file , $energy_cut , $energy_col ) ;
	print "$file\n" ;
	open FILE , "| /tmp/$$.gnuplot > $png_file" ;
print FILE <<EOF;
set term png
set title "$file"
set xrange [$Xmin:$Xmax] 
set yrange [$Ymin:$Ymax] 
splot "$out_file" using $colX:$colY:$colZ w dots
EOF
	close FILE ;
	`cat $out_file >> $movie.xyz` ;
	`zip $movie.xyz.zip $out_file` ;
	unlink $out_file ;
}
unlink "/tmp/$$.gnuplot" ;
`cp $dir/convert /tmp/$$.convert` ;
`chmod 775 /tmp/$$.convert` ;
my $last = $files[ -1 + scalar @files ] ;
`export LD_LIBRARY_PATH=$dir ; /tmp/$$.convert -delay $delay Out*.chkpt.png -delay 300 $last.png $movie` ;
`rm /tmp/$$.convert` ;
#`rm *.png` ;
`rm *.chkpt` ;
`mv $movie.xyz $movie.txt` ;
sub filter
{
	my ( $in , $out , $value , $column ) = @_ ;
	open IN , $in ;
	open OUT , ">$out" ;
	while( $line = <IN> )
	{
		if( $line =~ /^#/ )
		{
			next ;
		}
		my ( @array ) = split( / +/ , $line ) ;
		if( $array[ $column - 1 ] > $value )
		{
			print OUT $line ;
		}
	}
	close IN ;
	close OUT ;
}
