#!/usr/bin/perl
	
use sigtrap 'handler', \&cleanup , 'error-signals' ;
$SIG{PIPE}=\&trap; $SIG{QUIT}=\&trap; $SIG{INT}=\&trap; $SIG{STOP}=\&trap; $SIG{HUP}=\&trap;

use File::Path;
use File::Copy;
use File::Basename;
use Cwd;

sub trap
{
        debug( "Stop!" ) ;
        &cleanup ;
}

my ( $mode , $parameters , $xyz , $output_file , $xyzout_file ) = @ARGV ;
my $cwd = getcwd ;
my $dir = dirname($0) ; 
my $tmp = "/scratch/sgeadmin";
my $cmd = '' ;
if( $mode eq 'crack' ) {
	my @files = <$dir/*.dat>;
	foreach my $file ( @files ) 
	{
		copy($file, $cwd)
	}
	#`cp $dir/*.dat $cwd` ;
	$col = 6 ;
	$cmd = 'imd_nve_eam4point_deform_stress' ;
} 
elsif( $mode eq 'nanowire' ) {
	my @files = <$dir/*.dat>;
	foreach my $file ( @files ) 
	{
		copy($file, $cwd)
	}
	#`cp $dir/*.dat $cwd` ;
	$col = 6 ;
	$cmd = 'imd_nve_eam4point_deform_stress' ;

}
elsif( $mode eq 'elastic' ) {
	
	$col = 8 ;
	$cmd = 'imd_nve_pair_lj_glok_homdef_stress' ;
}
else
{
	print "Usage: $0 mode parameters xyz output_file xyzout_file\n" ;
	print "ARGS: " , join( "\n" , @ARGV ) . "\n" ;
	die "Unknown mode" ;
}

if( -f "$dir/$cmd" )
{
	my $out = "imd_out.txt" ;
	my $err = "imd_err.txt" ;
	open FILE, ">cmd.sh" ;
	print FILE '#!/bin/bash' ;
	print FILE "\nsource \$HOME/.bash_profile" ;
	#print FILE "\nenv" ;
    print FILE "\nmkdir $tmp/$$";
    print FILE "\nmv $cwd/* $tmp/$$/";
	print FILE "\nhostname -s > $cwd/mycwd";
	print FILE "\necho  $tmp/$$ >> $cwd/mycwd";
	print FILE "\ncp $dir/$cmd $tmp/$$/$$.cmd" ;
	print FILE "\nchmod 755 $tmp/$$/$$.cmd" ;
    print FILE "\ncd $tmp/$$";
	print FILE "\n$tmp/$$/$$.cmd -p $parameters" ;
	print FILE "\nrm $tmp/$$/$$.cmd";
	print FILE "\nfind *.chkpt -exec bash $dir/imdrun-run_py.sh {} \\;" ;
	print FILE "\nzip $output_file *.chkpt.xyz *.chkpt" ;
	print FILE "\ncat *.chkpt > tmp.txt" ;
	print FILE "\ncat *.chkpt.xyz > VMDMovie.xyz" ;
	print FILE "\npython $dir/chkpt2xyz_resc.py tmp.txt $xyzout_file 1" ;
	print FILE "\nrm tmp.txt" ;
	print FILE "\nrm *.chkpt" ;
	print FILE "\nrm *.chkpt.xyz" ;
	print FILE "\nrm *.itr" ;
	print FILE "\ncp $dir/gnuplot $tmp/$$/$$.gnuplot" ;
	print FILE "\nchmod 775 $tmp/$$/$$.gnuplot" ;
	print FILE "\n$tmp/$$/$$.gnuplot <<EOF;" ;
	print FILE "\nset term png" ;
	print FILE "\nset out 'EngPlot.png'" ;
	print FILE "\nset title '$mode'" ;
	print FILE "\nplot \"`ls *.eng | head -1`\" u " . $col . ", \"`ls *.eng | head -1`\" u " . ( $col + 1 ) . ",\"`ls *.eng | head -1`\" u " . ( $col + 2 ) ;
	print FILE "\nEOF\n" ;
	print FILE "\nrm $tmp/$$/$$.gnuplot" ;
	print FILE "\nrm $tmp/$$/$$.cmd" ;
    print FILE "\nrm $tmp/$$/*.dat";
    print FILE "\nmv $tmp/$$/* $cwd/";
    print FILE "\nrmdir $tmp/$$";
	close FILE ;
	chmod 0755, cmd.sh;
	my $jobid = &run( "$cwd/cmd.sh" , $cwd , undef , $out , $err ) ;
	@jobid = ( $jobid ) ;
	&waitFor( $jobid ) ;
=head
my $png_file = "engplot.png" ;
chomp( my $out_file = `ls *.eng` ) ;
`cp $dir/gnuplot /tmp/$$.gnuplot` ;
`chmod 755 /tmp/$$.gnuplot` ;
open FILE , "| /tmp/$$.gnuplot > $png_file" ;
print FILE <<EOF;
set term png
set title "$mode"
plot "$out_file" u 8 , "$out_file" u 9 , "$out_file" u 10
EOF
close FILE ;
unlink "/tmp/$$.gnuplot" ;
=cut
}
else
{
	die "Command missing $dir/$cmd" ;
}

sub run
{
        my ( $cmd , $cwd , $in , $out , $err ) = @_ ;
        my $jobid ;
        my $cmdLine = "cd $cwd ; qsub -S /bin/bash -cwd -j n -o $out -e $err $cmd " ;
        &debug( "$cmdLine" ) ;
        my $result = `$cmdLine` ;
        if( $result =~ /Your job ([0-9]+) .* has been submitted/mig )
        {
                $jobid = $1 ;
        }
        return $jobid ;
}

sub waitFor
{
        my @jobid = @_ ;
        print "Waiting for " . join( "," , @jobid ) . "\n" ;
        my %jobs = map { $_ => 1 } @jobid ;
        while( 1 ) {
        my $wait = 0 ;
        my @qstat = `qstat` ;
        #print "Qstat is : " . join( "\n" , @qstat ) . "\n" ;
        foreach( @qstat )
        {
                if( /\s*([0-9]+)\s+/ )
                {
                        my $job = $1 ;
                        if( defined( $jobs{$job} ) )
                        {
                                $wait = 1 ;
                                &debug( "Waiting for $job - still in queue" ) ;
                                last ;
                        }
                }
        }
        if( $wait == 0 )
        {
                last ;
        }
        else
        {
                sleep 2 ;
        }
        }
	sleep 2 ;
}

sub cleanup
{
        if( $handled < 10 )
        {

        &debug( "removing " . join( ' ' , @jobid ) . "\n" ) ;
        my $tasklist = join( " " , @jobid ) ;
        `qdel $tasklist` ;
        $handled = $handled + 1 ;

	my $list = ();
	if ( -f "$cwd/mycwd" ) {
		open (FILE, "$cwd/mycwd");
		foreach $line (<FILE>) {
			chomp $line;
			push @list, $line;
		}
		close (FILE);
		my $command = "ssh @list[0] rm -rf @list[1]";
		`echo "$command" >> /home/gpserver/iran`;
		`$command`;
	} else {
		`echo "file not created" >> /home/gpserver/iran`;
	}

	&debug( "removing $cwd" ) ;
	$cwd = getcwd ;
	rmtree($cwd) ;
	`echo "cleanup in imdrun-run.pl" >> /home/gpserver/iran`;
	exit;
        }
}

sub debug
{
        print STDERR join( "\n" , @_ ) . "\n" ;
        open FILE , ">>myError.log" ;
        print FILE join( "\n" , @_ ) . "\n" ;
        close FILE ;
}

